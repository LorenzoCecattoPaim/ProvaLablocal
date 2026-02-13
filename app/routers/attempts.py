from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import ExerciseAttempt, User
from app.schemas import AttemptCreate, AttemptResponse, StatsResponse, ProgressResponse
from app.auth import get_current_user

router = APIRouter(prefix="/attempts", tags=["Tentativas"])

@router.get("", response_model=List[AttemptResponse])
def get_attempts(
    limit: int = Query(50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter histórico de tentativas do usuário"""
    attempts = db.query(ExerciseAttempt).options(
        joinedload(ExerciseAttempt.exercise)
    ).filter(
        ExerciseAttempt.user_id == current_user.id
    ).order_by(
        ExerciseAttempt.created_at.desc()
    ).limit(limit).all()
    
    return attempts

@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter estatísticas do usuário"""
    attempts = db.query(ExerciseAttempt).filter(
        ExerciseAttempt.user_id == current_user.id
    ).all()
    
    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)
    accuracy = round((correct / total * 100)) if total > 0 else 0
    
    return StatsResponse(total=total, correct=correct, accuracy=accuracy)

@router.get("/progress", response_model=ProgressResponse)
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter dados de progresso do usuário"""
    attempts = db.query(ExerciseAttempt).options(
        joinedload(ExerciseAttempt.exercise)
    ).filter(
        ExerciseAttempt.user_id == current_user.id
    ).order_by(
        ExerciseAttempt.created_at.desc()
    ).limit(100).all()
    
    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)
    accuracy = round((correct / total * 100)) if total > 0 else 0
    
    return ProgressResponse(
        attempts=attempts,
        stats=StatsResponse(total=total, correct=correct, accuracy=accuracy)
    )

@router.post("", response_model=AttemptResponse)
def create_attempt(
    attempt_data: AttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registrar nova tentativa de exercício"""
    new_attempt = ExerciseAttempt(
        user_id=current_user.id,
        exercise_id=attempt_data.exercise_id,
        user_answer=attempt_data.user_answer,
        is_correct=attempt_data.is_correct,
        time_spent_seconds=attempt_data.time_spent_seconds
    )
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)
    
    # Carregar o exercício relacionado
    db.refresh(new_attempt, ['exercise'])
    
    return new_attempt
