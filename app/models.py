import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, Enum as SQLEnum, JSON, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class DifficultyLevel(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class SubjectType(str, enum.Enum):
    algebra = "algebra"
    geometry = "geometry"
    calculus = "calculus"
    statistics = "statistics"
    trigonometry = "trigonometry"
    arithmetic = "arithmetic"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    profile = relationship("Profile", back_populates="user", uselist=False)
    attempts = relationship("ExerciseAttempt", back_populates="user")

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    plan = Column(String(50), nullable=False, default="free")
    subscription_status = Column(String(50), nullable=False, default="none")
    trial_active = Column(Boolean, nullable=False, default=True)
    trial_expires_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    hotmart_transaction_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="profile")

class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # Array of options
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False)
    subject = Column(SQLEnum(SubjectType), nullable=False)
    is_premium = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    attempts = relationship("ExerciseAttempt", back_populates="exercise")

class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(Uuid(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_spent_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="attempts")
    exercise = relationship("Exercise", back_populates="attempts")


class PaymentEventLog(Base):
    __tablename__ = "payment_event_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_key = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    buyer_email = Column(String(255), nullable=True)
    transaction_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    outcome = Column(String(50), nullable=False, default="processed")
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    purpose = Column(String(50), nullable=False, default="signup", index=True)
    code_hash = Column(String(64), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    verified = Column(Boolean, nullable=False, default=False)
    consumed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
