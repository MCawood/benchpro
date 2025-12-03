"""API Token Pydantic schemas."""

from datetime import datetime
from typing import Optional

from app.schemas.common import BaseSchema


class ApiTokenBase(BaseSchema):
    """Base API token schema."""

    name: str


class ApiTokenCreate(ApiTokenBase):
    """Schema for creating a new API token."""

    pass


class ApiTokenRead(ApiTokenBase):
    """Schema for reading API token data (without the actual token)."""

    id: int
    created_at: datetime
    revoked_at: Optional[datetime] = None


class ApiTokenCreated(ApiTokenRead):
    """Schema returned when a token is created (includes plain-text token once)."""

    token: str  # Plain-text token, shown only once


class ApiTokenList(BaseSchema):
    """Schema for listing user's tokens."""

    tokens: list[ApiTokenRead]

