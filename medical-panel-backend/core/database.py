from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Default to SQLite file in the backend directory if DATABASE_URL not set
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models (User already defines its own Base, but we expose a common Base here)
Base = declarative_base()

def get_db():
    """FastAPI dependency that provides a DB session and ensures it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
