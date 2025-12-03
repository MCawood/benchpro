"""User service for CRUD operations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import CRUDBase


class UserService(CRUDBase[User, UserCreate, UserUpdate]):
    """Service for User operations."""

    async def get_by_external_id(
        self, db: AsyncSession, external_id: str
    ) -> Optional[User]:
        """Get user by external ID (IdP subject)."""
        result = await db.execute(
            select(User).where(User.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self, db: AsyncSession, *, external_id: str, **kwargs
    ) -> tuple[User, bool]:
        """Get existing user or create new one.

        Returns tuple of (user, created) where created is True if new user.
        """
        user = await self.get_by_external_id(db, external_id)
        if user:
            return user, False

        # Create new user
        user_create = UserCreate(external_id=external_id, **kwargs)
        user = await self.create(db, obj_in=user_create)
        return user, True


# Singleton instance
user_service = UserService(User)

