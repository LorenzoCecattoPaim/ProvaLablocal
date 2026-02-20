from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import TRIAL_DAYS
from app.database import get_db
from app.models import Profile, User


def utcnow() -> datetime:
    return datetime.utcnow()


def initialize_trial(profile: Profile) -> None:
    profile.plan = "free"
    profile.subscription_status = "none"
    profile.trial_active = True
    profile.trial_expires_at = utcnow() + timedelta(days=TRIAL_DAYS)
    profile.subscription_expires_at = None
    profile.hotmart_transaction_id = None


def ensure_trial_not_expired(profile: Profile) -> bool:
    if not profile.trial_active or not profile.trial_expires_at:
        return False
    if profile.trial_expires_at > utcnow():
        return False
    profile.trial_active = False
    return True


def is_subscription_active(profile: Profile) -> bool:
    if profile.plan != "premium" or profile.subscription_status != "active":
        return False
    if profile.subscription_expires_at and profile.subscription_expires_at <= utcnow():
        return False
    return True


def has_premium_access(profile: Profile) -> bool:
    if is_subscription_active(profile):
        return True
    return bool(profile.trial_active and profile.trial_expires_at and profile.trial_expires_at > utcnow())


def get_or_create_profile(db: Session, user: User) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile:
        return profile
    profile = Profile(user_id=user.id)
    initialize_trial(profile)
    db.add(profile)
    db.flush()
    return profile


def get_current_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Profile:
    profile = get_or_create_profile(db, current_user)
    changed = ensure_trial_not_expired(profile)
    if changed:
        db.commit()
        db.refresh(profile)
    return profile


def require_premium_access(profile: Profile = Depends(get_current_profile)) -> Profile:
    if has_premium_access(profile):
        return profile
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Plano premium inativo. Faça upgrade para continuar.",
    )
