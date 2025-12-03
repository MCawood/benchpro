"""SavedView service for CRUD operations."""

from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import SavedView, SavedViewVisibility
from app.schemas.saved_view import SavedViewCreate, SavedViewUpdate
from app.services.base import CRUDBase


class SavedViewService(CRUDBase[SavedView, SavedViewCreate, SavedViewUpdate]):
    """Service for SavedView operations."""

    async def get_with_owner(
        self, db: AsyncSession, id: int
    ) -> Optional[SavedView]:
        """Get saved view with owner loaded."""
        result = await db.execute(
            select(SavedView)
            .where(SavedView.id == id)
            .options(selectinload(SavedView.owner))
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        scope: str = "all",  # "mine", "shared", "all"
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SavedView]:
        """List saved views based on scope.

        - mine: Only user's own views
        - shared: Only public views from others
        - all: User's own views + all public views
        """
        query = select(SavedView).options(selectinload(SavedView.owner))

        if scope == "mine":
            query = query.where(SavedView.owner_user_id == user_id)
        elif scope == "shared":
            query = query.where(
                SavedView.visibility == SavedViewVisibility.PUBLIC,
                SavedView.owner_user_id != user_id,
            )
        else:  # "all"
            query = query.where(
                or_(
                    SavedView.owner_user_id == user_id,
                    SavedView.visibility == SavedViewVisibility.PUBLIC,
                )
            )

        query = query.order_by(SavedView.updated_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        obj_in: SavedViewCreate,
    ) -> SavedView:
        """Create a saved view for a user."""
        db_view = SavedView(
            owner_user_id=user_id,
            name=obj_in.name,
            description=obj_in.description,
            config=obj_in.config.model_dump(),
            visibility=obj_in.visibility,
        )
        db.add(db_view)
        await db.commit()
        await db.refresh(db_view)
        return db_view

    async def can_access(
        self, db: AsyncSession, view_id: int, user_id: int
    ) -> bool:
        """Check if a user can access a saved view."""
        view = await self.get(db, view_id)
        if not view:
            return False

        # Owner can always access
        if view.owner_user_id == user_id:
            return True

        # Public views are accessible to all
        return view.visibility == SavedViewVisibility.PUBLIC

    async def can_modify(
        self, db: AsyncSession, view_id: int, user_id: int, is_admin: bool = False
    ) -> bool:
        """Check if a user can modify a saved view."""
        view = await self.get(db, view_id)
        if not view:
            return False

        # Admins can modify any view
        if is_admin:
            return True

        # Only owner can modify
        return view.owner_user_id == user_id


# Singleton instance
saved_view_service = SavedViewService(SavedView)

