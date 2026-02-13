from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.database import get_db
from app.models import Exercise, User
from app.schemas import ExerciseResponse, ExerciseCreate
from app.auth import get_current_user

router = APIRouter(prefix="/exercises", tags=["Exercícios"])

@router.get("", response_model=List[ExerciseResponse])
def list_exercises(
    subject: Optional[str] = Query(None, description="Filtrar por matéria"),
    difficulty: Optional[str] = Query(None, description="Filtrar por dificuldade"),
    limit: int = Query(50, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar exercícios com filtros opcionais"""
    query = db.query(Exercise)
    
    if subject:
        query = query.filter(Exercise.subject == subject)
    if difficulty:
        query = query.filter(Exercise.difficulty == difficulty)
    
    exercises = query.order_by(Exercise.created_at.desc()).limit(limit).all()
    return exercises

@router.get("/random", response_model=ExerciseResponse)
def get_random_exercise(
    subject: str = Query(..., description="Matéria do exercício"),
    difficulty: str = Query(..., description="Dificuldade do exercício"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter um exercício aleatório por matéria e dificuldade"""
    exercise = db.query(Exercise).filter(
        Exercise.subject == subject,
        Exercise.difficulty == difficulty
    ).order_by(func.random()).first()
    
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum exercício encontrado para {subject} ({difficulty})"
        )
    
    return exercise

@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter exercício por ID"""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercício não encontrado"
        )
    return exercise

@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise_data: ExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Criar novo exercício"""
    new_exercise = Exercise(
        question=exercise_data.question,
        options=exercise_data.options,
        correct_answer=exercise_data.correct_answer,
        explanation=exercise_data.explanation,
        difficulty=exercise_data.difficulty,
        subject=exercise_data.subject
    )
    db.add(new_exercise)
    db.commit()
    db.refresh(new_exercise)
    return new_exercise
