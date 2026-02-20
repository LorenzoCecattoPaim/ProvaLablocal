from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import Exercise, ExerciseAttempt, Profile, User
from app.schemas import AttemptCreate, AttemptResponse, ProgressResponse, StatsResponse
from app.services.subscription_service import get_current_profile, has_premium_access

router = APIRouter(prefix="/attempts", tags=["Tentativas"])


@router.get("", response_model=List[AttemptResponse])
def get_attempts(
    limit: int = Query(50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtem historico de tentativas do usuario."""
    attempts = (
        db.query(ExerciseAttempt)
        .options(joinedload(ExerciseAttempt.exercise))
        .filter(ExerciseAttempt.user_id == current_user.id)
        .order_by(ExerciseAttempt.created_at.desc())
        .limit(limit)
        .all()
    )
    return attempts


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtem estatisticas do usuario."""
    attempts = db.query(ExerciseAttempt).filter(ExerciseAttempt.user_id == current_user.id).all()
    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)
    accuracy = round((correct / total * 100)) if total > 0 else 0
    return StatsResponse(total=total, correct=correct, accuracy=accuracy)


@router.get("/progress", response_model=ProgressResponse)
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtem dados de progresso do usuario."""
    attempts = (
        db.query(ExerciseAttempt)
        .options(joinedload(ExerciseAttempt.exercise))
        .filter(ExerciseAttempt.user_id == current_user.id)
        .order_by(ExerciseAttempt.created_at.desc())
        .limit(100)
        .all()
    )
    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)
    accuracy = round((correct / total * 100)) if total > 0 else 0
    return ProgressResponse(
        attempts=attempts,
        stats=StatsResponse(total=total, correct=correct, accuracy=accuracy),
    )


@router.post("", response_model=AttemptResponse)
def create_attempt(
    attempt_data: AttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_profile),
):
    """Registra nova tentativa de exercicio."""
    exercise = db.query(Exercise).filter(Exercise.id == attempt_data.exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercicio nao encontrado")
    if exercise.is_premium and not has_premium_access(profile):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conteudo premium. Faca upgrade para registrar tentativas.",
        )

    new_attempt = ExerciseAttempt(
        user_id=current_user.id,
        exercise_id=attempt_data.exercise_id,
        user_answer=attempt_data.user_answer,
        is_correct=attempt_data.is_correct,
        time_spent_seconds=attempt_data.time_spent_seconds,
    )
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)
    db.refresh(new_attempt, ["exercise"])
    return new_attempt
