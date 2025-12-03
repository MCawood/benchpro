"""Provenance-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from app.db.models import ArtifactEncoding
from app.schemas.common import BaseSchema


# --- Provenance Metadata Schemas ---


class ProvenanceMetadataBase(BaseSchema):
    """Base provenance metadata schema."""

    key: str
    value_text: Optional[str] = None
    value_json: Optional[Any] = None  # Can be dict or list


class ProvenanceMetadataCreate(ProvenanceMetadataBase):
    """Schema for creating provenance metadata."""

    pass


class ProvenanceMetadataRead(ProvenanceMetadataBase):
    """Schema for reading provenance metadata."""

    id: int
    task_run_id: int


# --- Provenance Artifact Schemas ---


class ProvenanceArtifactBase(BaseSchema):
    """Base provenance artifact schema."""

    name: str
    content_type: str
    encoding: ArtifactEncoding = ArtifactEncoding.RAW


class ProvenanceArtifactCreate(ProvenanceArtifactBase):
    """Schema for creating a provenance artifact."""

    data: bytes  # Raw or gzip-compressed data

    @property
    def size_bytes(self) -> int:
        return len(self.data)


class ProvenanceArtifactRead(ProvenanceArtifactBase):
    """Schema for reading artifact metadata (without data)."""

    id: int
    task_run_id: int
    size_bytes: int
    created_at: datetime


class ProvenanceArtifactContent(BaseSchema):
    """Schema for artifact content response."""

    id: int
    name: str
    content_type: str
    encoding: ArtifactEncoding
    size_bytes: int
    content: Optional[str] = None  # Text content (for mode=text)
    truncated: bool = False


# --- Combined Provenance Response ---


class TaskProvenanceResponse(BaseSchema):
    """Combined provenance response for a task run."""

    metadata: list[ProvenanceMetadataRead]
    artifacts: list[ProvenanceArtifactRead]

    # Parsed/structured provenance for display
    modules: Optional[list[str]] = None
    environment: Optional[dict[str, str]] = None
    scheduler: Optional[dict[str, Any]] = None
    git_commit: Optional[str] = None

