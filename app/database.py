from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_profile_columns() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "profiles" not in tables:
        return

    existing = {column["name"] for column in inspector.get_columns("profiles")}
    statements: list[str] = []
    if "plan" not in existing:
        statements.append("ALTER TABLE profiles ADD COLUMN plan VARCHAR(50) NOT NULL DEFAULT 'free'")
    if "subscription_status" not in existing:
        statements.append("ALTER TABLE profiles ADD COLUMN subscription_status VARCHAR(50) NOT NULL DEFAULT 'none'")
    if "trial_active" not in existing:
        statements.append("ALTER TABLE profiles ADD COLUMN trial_active BOOLEAN NOT NULL DEFAULT TRUE")
    if "trial_expires_at" not in existing:
        statements.append("ALTER TABLE profiles ADD COLUMN trial_expires_at TIMESTAMP NULL")
    if "subscription_expires_at" not in existing:
        statements.append("ALTER TABLE profiles ADD COLUMN subscription_expires_at TIMESTAMP NULL")
    if "hotmart_transaction_id" not in existing:
        statements.append("ALTER TABLE profiles ADD COLUMN hotmart_transaction_id VARCHAR(255) NULL")

    if not statements:
        return

    with engine.begin() as connection:
        for stmt in statements:
            connection.execute(text(stmt))


def _ensure_exercise_columns() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "exercises" not in tables:
        return

    existing = {column["name"] for column in inspector.get_columns("exercises")}
    if "is_premium" in existing:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE exercises ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT FALSE"))


def init_db() -> None:
    # Importing models here guarantees table metadata is registered before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_profile_columns()
    _ensure_exercise_columns()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
