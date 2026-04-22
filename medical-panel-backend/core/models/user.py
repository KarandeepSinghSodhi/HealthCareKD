from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)  # Google "sub" claim
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
