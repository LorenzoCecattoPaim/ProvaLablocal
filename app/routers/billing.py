from fastapi import APIRouter, Depends

from app.config import HOTMART_CHECKOUT_URL
from app.models import Profile
from app.schemas import SubscriptionStatusResponse
from app.services.subscription_service import get_current_profile, has_premium_access

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/status", response_model=SubscriptionStatusResponse)
def get_billing_status(profile: Profile = Depends(get_current_profile)):
    """Expose assinatura/trial para o frontend decidir bloqueios e CTA de upgrade."""
    return SubscriptionStatusResponse(
        plan=profile.plan,
        subscription_status=profile.subscription_status,
        trial_active=profile.trial_active,
        trial_expires_at=profile.trial_expires_at,
        subscription_expires_at=profile.subscription_expires_at,
        premium_access=has_premium_access(profile),
        upgrade_url=HOTMART_CHECKOUT_URL or None,
    )
