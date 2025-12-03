"""BenchmarkDefinition Pydantic schemas."""

from typing import Any, Optional

from app.schemas.application import ApplicationSummary
from app.schemas.common import BaseSchema, TimestampMixin


class BenchmarkDefinitionBase(BaseSchema):
    """Base benchmark definition schema."""

    label: str
    description: Optional[str] = None
    default_primary_fom_name: Optional[str] = None
    fom_schema: Optional[dict[str, Any]] = None
    extra: Optional[dict[str, Any]] = None


class BenchmarkDefinitionCreate(BenchmarkDefinitionBase):
    """Schema for creating a benchmark definition."""

    application_id: Optional[int] = None


class BenchmarkDefinitionUpdate(BaseSchema):
    """Schema for updating a benchmark definition."""

    label: Optional[str] = None
    application_id: Optional[int] = None
    description: Optional[str] = None
    default_primary_fom_name: Optional[str] = None
    fom_schema: Optional[dict[str, Any]] = None
    extra: Optional[dict[str, Any]] = None


class BenchmarkDefinitionRead(BenchmarkDefinitionBase, TimestampMixin):
    """Schema for reading benchmark definition data."""

    id: int
    application_id: Optional[int] = None
    application: Optional[ApplicationSummary] = None


class BenchmarkDefinitionSummary(BaseSchema):
    """Minimal benchmark definition info for embedding."""

    id: int
    label: str
    description: Optional[str] = None
    default_primary_fom_name: Optional[str] = None

