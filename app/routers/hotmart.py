import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import HOTMART_WEBHOOK_TOKEN
from app.database import get_db
from app.models import PaymentEventLog, User
from app.services.email_service import send_premium_welcome_email
from app.services.subscription_service import get_or_create_profile

router = APIRouter(prefix="/api/hotmart", tags=["Hotmart"])
logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = {
    "PURCHASE_APPROVED",
    "SUBSCRIPTION_CHARGED",
    "SUBSCRIPTION_CANCELED",
    "SUBSCRIPTION_EXPIRED",
}


def _parse_datetime(value: str | int | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, int):
        # Hotmart can send unix timestamps in seconds/milliseconds.
        if value > 10_000_000_000:
            return datetime.utcfromtimestamp(value / 1000)
        return datetime.utcfromtimestamp(value)
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _extract_subscription_expiry(payload_data: dict) -> datetime | None:
    subscription = payload_data.get("subscription") or {}
    transaction = payload_data.get("transaction") or {}
    candidates = [
        subscription.get("access_until"),
        subscription.get("next_charge_date"),
        subscription.get("end_date"),
        transaction.get("access_until"),
    ]
    for candidate in candidates:
        dt = _parse_datetime(candidate)
        if dt:
            return dt
    return None


def _validate_hotmart_origin(request: Request, payload: dict) -> None:
    if not HOTMART_WEBHOOK_TOKEN:
        return
    token = (
        request.headers.get("x-hotmart-hottok")
        or request.headers.get("x-hotmart-token")
        or str(payload.get("hottok") or "")
    )
    if token != HOTMART_WEBHOOK_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook token invalido")


def _build_event_key(event: str, payload_data: dict) -> str:
    transaction = payload_data.get("transaction") or {}
    subscription = payload_data.get("subscription") or {}
    payload_seed = json.dumps(payload_data, sort_keys=True, default=str)
    raw_key = "|".join(
        [
            event,
            str(transaction.get("id") or transaction.get("transaction") or ""),
            str(subscription.get("id") or ""),
            hashlib.sha256(payload_seed.encode("utf-8")).hexdigest()[:16],
        ]
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@router.post("/webhook")
async def hotmart_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON invalido") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload invalido")

    _validate_hotmart_origin(request, payload)

    event = str(payload.get("event") or "").upper()
    data = payload.get("data") or {}

    if event not in SUPPORTED_EVENTS:
        return {"ok": True, "ignored": True}

    buyer = data.get("buyer") or {}
    email = str(buyer.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email do comprador ausente")

    event_key = _build_event_key(event, data)
    existing = db.query(PaymentEventLog).filter(PaymentEventLog.event_key == event_key).first()
    if existing:
        return {"ok": True, "duplicate": True}

    transaction = data.get("transaction") or {}
    transaction_id = str(transaction.get("id") or transaction.get("transaction") or "")
    transaction_status = str(transaction.get("status") or "")

    event_log = PaymentEventLog(
        event_key=event_key,
        event_type=event,
        buyer_email=email,
        transaction_id=transaction_id or None,
        status=transaction_status or None,
        payload=payload,
        outcome="processed",
    )
    db.add(event_log)

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        event_log.outcome = "user_not_found"
        db.commit()
        logger.error("Webhook Hotmart sem usuario correspondente: %s", email)
        return {"ok": True, "error": "user_not_found"}

    profile = get_or_create_profile(db, user)
    subscription_expires_at = _extract_subscription_expiry(data)

    if event == "PURCHASE_APPROVED":
        profile.plan = "premium"
        profile.subscription_status = "active"
        profile.trial_active = False
        profile.hotmart_transaction_id = transaction_id or profile.hotmart_transaction_id
        if subscription_expires_at:
            profile.subscription_expires_at = subscription_expires_at
        background_tasks.add_task(send_premium_welcome_email, user.email, profile.full_name)
    elif event == "SUBSCRIPTION_CHARGED":
        profile.plan = "premium"
        profile.subscription_status = "active"
        profile.trial_active = False
        if transaction_id:
            profile.hotmart_transaction_id = transaction_id
        if subscription_expires_at:
            profile.subscription_expires_at = subscription_expires_at
    elif event == "SUBSCRIPTION_CANCELED":
        profile.subscription_status = "canceled"
    elif event == "SUBSCRIPTION_EXPIRED":
        profile.plan = "free"
        profile.subscription_status = "expired"
        profile.trial_active = False

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"ok": True, "duplicate": True}

    return {"ok": True}
