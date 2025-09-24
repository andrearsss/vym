import uuid
from typing import Optional
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, EmailStr
from database import Base

class User(Base):
    """
    SQLAlchemy model for the User table
    - `id`
    - `email`
    - `username`
    - `password_hash`
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    def __repr__(self):
        return f"<User(email='{self.email}', username='{self.username}')>"
    
# Pydantic models
class UserSignup(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
