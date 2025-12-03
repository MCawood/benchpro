"""Application service for CRUD operations."""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.base import CRUDBase


class ApplicationService(CRUDBase[Application, ApplicationCreate, ApplicationUpdate]):
    """Service for Application operations."""

    async def get_by_label(
        self, db: AsyncSession, label: str
    ) -> Optional[Application]:
        """Get application by label."""
        result = await db.execute(
            select(Application).where(Application.label == label)
        )
        return result.scalar_one_or_none()

    async def get_by_label_system_version(
        self,
        db: AsyncSession,
        label: str,
        system: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Optional[Application]:
        """Get application by label, system, and version combination."""
        query = select(Application).where(Application.label == label)
        if system is not None:
            query = query.where(Application.system == system)
        if version is not None:
            query = query.where(Application.version == version)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def find_or_create(
        self, db: AsyncSession, *, obj_in: ApplicationCreate
    ) -> tuple[Application, bool]:
        """Find existing application or create new one.

        Returns tuple of (application, created) where created is True if new.
        """
        existing = await self.get_by_label_system_version(
            db,
            label=obj_in.label,
            system=obj_in.system,
            version=obj_in.version,
        )
        if existing:
            return existing, False

        app = await self.create(db, obj_in=obj_in)
        return app, True

    async def search(
        self,
        db: AsyncSession,
        *,
        q: Optional[str] = None,
        system: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Application]:
        """Search applications with optional filters."""
        query = select(Application)

        if q:
            query = query.where(Application.label.ilike(f"%{q}%"))
        if system:
            query = query.where(Application.system == system)

        query = query.order_by(Application.label).offset(offset).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()


# Singleton instance
application_service = ApplicationService(Application)

