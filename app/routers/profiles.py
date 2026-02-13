from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Profile
from app.schemas import ProfileResponse, ProfileUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/profiles", tags=["Perfis"])

@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter perfil do usuário autenticado"""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil não encontrado"
        )
    return profile

@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    profile_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualizar perfil do usuário autenticado"""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        # Criar perfil se não existir
        profile = Profile(user_id=current_user.id)
        db.add(profile)
    
    # Atualizar campos
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    return profile
