"""User-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr

from app.db.models import UserRole
from app.schemas.common import BaseSchema, TimestampMixin


class UserBase(BaseSchema):
    """Base user schema with common fields."""

    external_id: str
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    """Schema for creating a new user."""

    pass


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None


class UserRead(UserBase, TimestampMixin):
    """Schema for reading user data."""

    id: int


class UserSummary(BaseSchema):
    """Minimal user info for embedding in other responses."""

    id: int
    external_id: str
    display_name: Optional[str] = None

