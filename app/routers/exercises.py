from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.auth import get_current_user
from app.database import get_db
from app.models import Exercise, Profile, User
from app.schemas import ExerciseCreate, ExerciseResponse
from app.services.subscription_service import get_current_profile, has_premium_access

router = APIRouter(prefix="/exercises", tags=["Exercicios"])


@router.get("", response_model=List[ExerciseResponse])
def list_exercises(
    subject: Optional[str] = Query(None, description="Filtrar por materia"),
    difficulty: Optional[str] = Query(None, description="Filtrar por dificuldade"),
    limit: int = Query(50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    profile: Profile = Depends(get_current_profile),
):
    """Lista exercicios com filtros opcionais."""
    query = db.query(Exercise)
    if subject:
        query = query.filter(Exercise.subject == subject)
    if difficulty:
        query = query.filter(Exercise.difficulty == difficulty)
    if not has_premium_access(profile):
        query = query.filter(Exercise.is_premium.is_(False))
    return query.order_by(Exercise.created_at.desc()).limit(limit).all()


@router.get("/random", response_model=ExerciseResponse)
def get_random_exercise(
    subject: str = Query(..., description="Materia do exercicio"),
    difficulty: str = Query(..., description="Dificuldade do exercicio"),
    db: Session = Depends(get_db),
    profile: Profile = Depends(get_current_profile),
):
    """Retorna um exercicio aleatorio por materia e dificuldade."""
    query = db.query(Exercise).filter(
        Exercise.subject == subject,
        Exercise.difficulty == difficulty,
    )
    if not has_premium_access(profile):
        query = query.filter(Exercise.is_premium.is_(False))
    exercise = query.order_by(func.random()).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum exercicio encontrado para os filtros",
        )
    return exercise


@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: UUID,
    db: Session = Depends(get_db),
    profile: Profile = Depends(get_current_profile),
):
    """Retorna exercicio por ID."""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercicio nao encontrado")
    if exercise.is_premium and not has_premium_access(profile):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conteudo premium. Faca upgrade para acessar.",
        )
    return exercise


@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise_data: ExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria novo exercicio."""
    _ = current_user
    new_exercise = Exercise(
        question=exercise_data.question,
        options=exercise_data.options,
        correct_answer=exercise_data.correct_answer,
        explanation=exercise_data.explanation,
        difficulty=exercise_data.difficulty,
        subject=exercise_data.subject,
        is_premium=exercise_data.is_premium,
    )
    db.add(new_exercise)
    db.commit()
    db.refresh(new_exercise)
    return new_exercise
