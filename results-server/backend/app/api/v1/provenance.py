"""Provenance retrieval endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.provenance import (
    ProvenanceArtifactContent,
    ProvenanceArtifactRead,
    ProvenanceMetadataRead,
    TaskProvenanceResponse,
)
from app.services import provenance_service, task_run_service

router = APIRouter()


@router.get("/task_runs/{task_run_id}/provenance", response_model=TaskProvenanceResponse)
async def get_task_provenance(
    db: DbSession,
    current_user: CurrentUser,
    task_run_id: int,
) -> TaskProvenanceResponse:
    """Get provenance data for a task run.

    Returns both metadata and artifact listings, plus
    structured provenance (modules, environment, scheduler).
    """
    # Verify task run exists
    task_run = await task_run_service.get(db, task_run_id)
    if not task_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task run not found",
        )

    # Get metadata and artifacts
    metadata = await provenance_service.get_metadata_for_task(db, task_run_id)
    artifacts = await provenance_service.get_artifacts_for_task(db, task_run_id)

    # Get structured provenance
    structured = await provenance_service.get_structured_provenance(db, task_run_id)

    return TaskProvenanceResponse(
        metadata=[ProvenanceMetadataRead.model_validate(m) for m in metadata],
        artifacts=[ProvenanceArtifactRead.model_validate(a) for a in artifacts],
        modules=structured.get("modules"),
        environment=structured.get("environment"),
        scheduler=structured.get("scheduler"),
        git_commit=structured.get("git_commit"),
    )


@router.get("/provenance_artifacts/{artifact_id}", response_model=None)
async def get_provenance_artifact(
    db: DbSession,
    current_user: CurrentUser,
    artifact_id: int,
    mode: str = Query("text", description="Response mode: 'text' or 'raw'"),
    max_bytes: Optional[int] = Query(None, description="Max bytes for text mode"),
):
    """Get artifact content.

    - mode=text: Returns JSON with text content (possibly truncated)
    - mode=raw: Returns raw binary stream with appropriate Content-Type
    """
    artifact = await provenance_service.get_artifact(db, artifact_id)

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    if mode == "raw":
        # Return raw binary data
        data = provenance_service.decompress_artifact(artifact)
        return Response(
            content=data,
            media_type=artifact.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{artifact.name}"',
                "Content-Length": str(len(data)),
            },
        )
    else:
        # Return text content
        text, truncated = provenance_service.get_artifact_text(artifact, max_bytes)

        return ProvenanceArtifactContent(
            id=artifact.id,
            name=artifact.name,
            content_type=artifact.content_type,
            encoding=artifact.encoding,
            size_bytes=artifact.size_bytes,
            content=text,
            truncated=truncated,
        )

