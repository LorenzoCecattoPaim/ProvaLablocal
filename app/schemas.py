from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# ========================
# Auth Schemas
# ========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str  # email
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ========================
# Profile Schemas
# ========================

class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

# ========================
# Exercise Schemas
# ========================

class ExerciseResponse(BaseModel):
    id: UUID
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: str
    subject: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ExerciseCreate(BaseModel):
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: str
    subject: str

# ========================
# Attempt Schemas
# ========================

class AttemptCreate(BaseModel):
    exercise_id: UUID
    user_answer: str
    is_correct: bool
    time_spent_seconds: Optional[int] = None

class AttemptResponse(BaseModel):
    id: UUID
    user_id: UUID
    exercise_id: UUID
    user_answer: str
    is_correct: bool
    time_spent_seconds: Optional[int] = None
    created_at: datetime
    exercise: Optional[ExerciseResponse] = None
    
    class Config:
        from_attributes = True

# ========================
# Stats Schemas
# ========================

class StatsResponse(BaseModel):
    total: int
    correct: int
    accuracy: int

class ProgressResponse(BaseModel):
    attempts: List[AttemptResponse]
    stats: StatsResponse
