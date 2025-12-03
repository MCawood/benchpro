"""BenchmarkDefinition service for CRUD operations."""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import BenchmarkDefinition
from app.schemas.benchmark_definition import (
    BenchmarkDefinitionCreate,
    BenchmarkDefinitionUpdate,
)
from app.services.base import CRUDBase


class BenchmarkDefinitionService(
    CRUDBase[BenchmarkDefinition, BenchmarkDefinitionCreate, BenchmarkDefinitionUpdate]
):
    """Service for BenchmarkDefinition operations."""

    async def get_by_label(
        self, db: AsyncSession, label: str
    ) -> Optional[BenchmarkDefinition]:
        """Get benchmark definition by label."""
        result = await db.execute(
            select(BenchmarkDefinition).where(BenchmarkDefinition.label == label)
        )
        return result.scalar_one_or_none()

    async def get_with_application(
        self, db: AsyncSession, id: int
    ) -> Optional[BenchmarkDefinition]:
        """Get benchmark definition with application loaded."""
        result = await db.execute(
            select(BenchmarkDefinition)
            .where(BenchmarkDefinition.id == id)
            .options(selectinload(BenchmarkDefinition.application))
        )
        return result.scalar_one_or_none()

    async def find_or_create(
        self, db: AsyncSession, *, obj_in: BenchmarkDefinitionCreate
    ) -> tuple[BenchmarkDefinition, bool]:
        """Find existing benchmark definition or create new one.

        Returns tuple of (benchmark_definition, created).
        """
        existing = await self.get_by_label(db, obj_in.label)
        if existing:
            return existing, False

        benchmark = await self.create(db, obj_in=obj_in)
        return benchmark, True

    async def search(
        self,
        db: AsyncSession,
        *,
        q: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[BenchmarkDefinition]:
        """Search benchmark definitions with optional filters."""
        query = select(BenchmarkDefinition)

        if q:
            query = query.where(BenchmarkDefinition.label.ilike(f"%{q}%"))

        query = query.order_by(BenchmarkDefinition.label).offset(offset).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()


# Singleton instance
benchmark_definition_service = BenchmarkDefinitionService(BenchmarkDefinition)

