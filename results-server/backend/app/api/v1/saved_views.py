"""Saved views endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.db.models import UserRole
from app.schemas.saved_view import (
    SavedViewCreate,
    SavedViewDetail,
    SavedViewSummary,
    SavedViewUpdate,
)
from app.schemas.user import UserSummary
from app.services import saved_view_service

router = APIRouter()


@router.get("", response_model=list[SavedViewSummary])
async def list_saved_views(
    db: DbSession,
    current_user: CurrentUser,
    scope: str = Query("all", description="Scope: 'mine', 'shared', or 'all'"),
) -> list[SavedViewSummary]:
    """List saved views based on scope.

    - mine: Only your own views
    - shared: Only public views from other users
    - all: Your views + all public views
    """
    if scope not in ("mine", "shared", "all"):
        scope = "all"

    views = await saved_view_service.list_for_user(
        db, current_user.id, scope=scope
    )

    summaries = []
    for v in views:
        owner_summary = None
        if v.owner:
            owner_summary = UserSummary(
                id=v.owner.id,
                external_id=v.owner.external_id,
                display_name=v.owner.display_name,
            )

        summaries.append(
            SavedViewSummary(
                id=v.id,
                name=v.name,
                description=v.description,
                visibility=v.visibility,
                owner=owner_summary,
                created_at=v.created_at,
                updated_at=v.updated_at,
            )
        )

    return summaries


@router.post("", response_model=SavedViewDetail, status_code=status.HTTP_201_CREATED)
async def create_saved_view(
    db: DbSession,
    current_user: CurrentUser,
    view_in: SavedViewCreate,
) -> SavedViewDetail:
    """Create a new saved view."""
    view = await saved_view_service.create_for_user(
        db, user_id=current_user.id, obj_in=view_in
    )

    return SavedViewDetail.model_validate(view)


@router.get("/{view_id}", response_model=SavedViewDetail)
async def get_saved_view(
    db: DbSession,
    current_user: CurrentUser,
    view_id: int,
) -> SavedViewDetail:
    """Get a saved view by ID."""
    # Check access
    can_access = await saved_view_service.can_access(db, view_id, current_user.id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved view not found",
        )

    view = await saved_view_service.get_with_owner(db, view_id)
    return SavedViewDetail.model_validate(view)


@router.put("/{view_id}", response_model=SavedViewDetail)
async def update_saved_view(
    db: DbSession,
    current_user: CurrentUser,
    view_id: int,
    view_in: SavedViewUpdate,
) -> SavedViewDetail:
    """Update a saved view."""
    is_admin = current_user.role == UserRole.ADMIN
    can_modify = await saved_view_service.can_modify(
        db, view_id, current_user.id, is_admin=is_admin
    )

    if not can_modify:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify this saved view",
        )

    view = await saved_view_service.get(db, view_id)
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved view not found",
        )

    # Prepare update data
    update_data = view_in.model_dump(exclude_unset=True)
    if "config" in update_data and update_data["config"]:
        update_data["config"] = update_data["config"].model_dump()

    updated = await saved_view_service.update(db, db_obj=view, obj_in=update_data)
    return SavedViewDetail.model_validate(updated)


@router.delete("/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_view(
    db: DbSession,
    current_user: CurrentUser,
    view_id: int,
) -> None:
    """Delete a saved view."""
    is_admin = current_user.role == UserRole.ADMIN
    can_modify = await saved_view_service.can_modify(
        db, view_id, current_user.id, is_admin=is_admin
    )

    if not can_modify:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete this saved view",
        )

    await saved_view_service.delete(db, id=view_id)

