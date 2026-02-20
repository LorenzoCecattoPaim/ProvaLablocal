from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Profile, User
from app.schemas import ProfileResponse, ProfileUpdate
from app.services.subscription_service import get_current_profile, get_or_create_profile

router = APIRouter(prefix="/profiles", tags=["Perfis"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(profile: Profile = Depends(get_current_profile)):
    """Retorna o perfil do usuario autenticado."""
    return profile


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    profile_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza o perfil do usuario autenticado."""
    profile = get_or_create_profile(db, current_user)
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
