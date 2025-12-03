"""Application Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from app.schemas.common import BaseSchema, TimestampMixin


class ApplicationBase(BaseSchema):
    """Base application schema."""

    label: str
    version: Optional[str] = None
    system: Optional[str] = None
    architecture: Optional[str] = None
    modules: Optional[list[str]] = None
    benchpro_version: Optional[str] = None
    build_user: Optional[str] = None
    build_time: Optional[datetime] = None
    extra: Optional[dict[str, Any]] = None


class ApplicationCreate(ApplicationBase):
    """Schema for creating an application."""

    pass


class ApplicationUpdate(BaseSchema):
    """Schema for updating an application."""

    label: Optional[str] = None
    version: Optional[str] = None
    system: Optional[str] = None
    architecture: Optional[str] = None
    modules: Optional[list[str]] = None
    benchpro_version: Optional[str] = None
    build_user: Optional[str] = None
    build_time: Optional[datetime] = None
    extra: Optional[dict[str, Any]] = None


class ApplicationRead(ApplicationBase, TimestampMixin):
    """Schema for reading application data."""

    id: int


class ApplicationSummary(BaseSchema):
    """Minimal application info for embedding in other responses."""

    id: int
    label: str
    version: Optional[str] = None
    system: Optional[str] = None
    architecture: Optional[str] = None

