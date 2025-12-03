"""Provenance service for retrieving provenance data."""

import gzip
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ArtifactEncoding, ProvenanceArtifact, TaskProvenanceMetadata


class ProvenanceService:
    """Service for provenance operations."""

    async def get_metadata_for_task(
        self, db: AsyncSession, task_run_id: int
    ) -> Sequence[TaskProvenanceMetadata]:
        """Get all provenance metadata for a task run."""
        result = await db.execute(
            select(TaskProvenanceMetadata)
            .where(TaskProvenanceMetadata.task_run_id == task_run_id)
            .order_by(TaskProvenanceMetadata.key)
        )
        return result.scalars().all()

    async def get_artifacts_for_task(
        self, db: AsyncSession, task_run_id: int
    ) -> Sequence[ProvenanceArtifact]:
        """Get all artifact metadata (without data) for a task run."""
        result = await db.execute(
            select(ProvenanceArtifact)
            .where(ProvenanceArtifact.task_run_id == task_run_id)
            .order_by(ProvenanceArtifact.name)
        )
        return result.scalars().all()

    async def get_artifact(
        self, db: AsyncSession, artifact_id: int
    ) -> Optional[ProvenanceArtifact]:
        """Get a single artifact by ID."""
        result = await db.execute(
            select(ProvenanceArtifact).where(ProvenanceArtifact.id == artifact_id)
        )
        return result.scalar_one_or_none()

    def decompress_artifact(self, artifact: ProvenanceArtifact) -> bytes:
        """Decompress artifact data if needed."""
        if artifact.encoding == ArtifactEncoding.GZIP:
            return gzip.decompress(artifact.data)
        return artifact.data

    def get_artifact_text(
        self,
        artifact: ProvenanceArtifact,
        max_bytes: Optional[int] = None,
    ) -> tuple[str, bool]:
        """Get artifact content as text.

        Returns tuple of (text_content, truncated).
        """
        data = self.decompress_artifact(artifact)

        truncated = False
        if max_bytes and len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = True

        # Attempt UTF-8 decode, fall back to latin-1
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")

        return text, truncated

    async def get_structured_provenance(
        self, db: AsyncSession, task_run_id: int
    ) -> dict:
        """Get structured provenance data for display.

        Extracts known keys into structured format.
        """
        metadata = await self.get_metadata_for_task(db, task_run_id)

        result = {
            "modules": None,
            "environment": None,
            "scheduler": None,
            "git_commit": None,
        }

        for meta in metadata:
            if meta.key == "modules":
                if meta.value_json:
                    result["modules"] = meta.value_json
                elif meta.value_text:
                    result["modules"] = meta.value_text.split("\n")
            elif meta.key == "environment":
                if meta.value_json:
                    result["environment"] = meta.value_json
            elif meta.key == "scheduler":
                if meta.value_json:
                    result["scheduler"] = meta.value_json
            elif meta.key == "git_commit":
                result["git_commit"] = meta.value_text

        return result


# Singleton instance
provenance_service = ProvenanceService()

