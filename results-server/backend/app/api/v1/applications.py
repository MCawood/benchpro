"""Application metadata endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.application import ApplicationRead
from app.schemas.common import PaginatedResponse
from app.services import application_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ApplicationRead])
async def list_applications(
    db: DbSession,
    current_user: CurrentUser,
    q: Optional[str] = Query(None, description="Search by label"),
    system: Optional[str] = Query(None, description="Filter by system"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[ApplicationRead]:
    """List applications with optional search and filters."""
    offset = (page - 1) * per_page

    applications = await application_service.search(
        db, q=q, system=system, offset=offset, limit=per_page
    )

    # Get total count (simplified - could optimize)
    total = await application_service.count(db)

    return PaginatedResponse.create(
        items=[ApplicationRead.model_validate(a) for a in applications],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    db: DbSession,
    current_user: CurrentUser,
    application_id: int,
) -> ApplicationRead:
    """Get a specific application by ID."""
    application = await application_service.get(db, application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return ApplicationRead.model_validate(application)

