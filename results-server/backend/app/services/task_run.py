"""TaskRun service for CRUD operations and submission handling."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Application,
    BenchmarkDefinition,
    FigureOfMerit,
    FomValueType,
    ProvenanceArtifact,
    TaskProvenanceMetadata,
    TaskRun,
    TaskStatus,
    User,
)
from app.schemas.application import ApplicationCreate
from app.schemas.benchmark_definition import BenchmarkDefinitionCreate
from app.schemas.task_run import TaskRunCreate, TaskRunFilters, TaskRunSubmission
from app.services.application import application_service
from app.services.base import CRUDBase
from app.services.benchmark_definition import benchmark_definition_service


class TaskRunService(CRUDBase[TaskRun, TaskRunCreate, TaskRunCreate]):
    """Service for TaskRun operations."""

    async def get_by_user_and_uuid(
        self, db: AsyncSession, user_id: int, task_uuid: UUID
    ) -> Optional[TaskRun]:
        """Get task run by user ID and task UUID (idempotency check)."""
        result = await db.execute(
            select(TaskRun).where(
                and_(TaskRun.user_id == user_id, TaskRun.task_uuid == task_uuid)
            )
        )
        return result.scalar_one_or_none()

    async def get_with_relations(
        self, db: AsyncSession, id: int
    ) -> Optional[TaskRun]:
        """Get task run with all related entities loaded."""
        result = await db.execute(
            select(TaskRun)
            .where(TaskRun.id == id)
            .options(
                selectinload(TaskRun.user),
                selectinload(TaskRun.application),
                selectinload(TaskRun.benchmark_definition),
                selectinload(TaskRun.figures_of_merit),
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        db: AsyncSession,
        *,
        filters: TaskRunFilters,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[TaskRun], int]:
        """List task runs with filters and pagination.

        Returns tuple of (task_runs, total_count).
        """
        query = select(TaskRun)
        count_query = select(func.count(TaskRun.id))

        # Apply filters
        if filters.system:
            query = query.where(TaskRun.system.in_(filters.system))
            count_query = count_query.where(TaskRun.system.in_(filters.system))

        if filters.architecture:
            query = query.where(TaskRun.architecture == filters.architecture)
            count_query = count_query.where(TaskRun.architecture == filters.architecture)

        if filters.status:
            query = query.where(TaskRun.status == filters.status)
            count_query = count_query.where(TaskRun.status == filters.status)

        if filters.node_count_min is not None:
            query = query.where(TaskRun.node_count >= filters.node_count_min)
            count_query = count_query.where(TaskRun.node_count >= filters.node_count_min)

        if filters.node_count_max is not None:
            query = query.where(TaskRun.node_count <= filters.node_count_max)
            count_query = count_query.where(TaskRun.node_count <= filters.node_count_max)

        if filters.submitted_after:
            query = query.where(TaskRun.submit_time >= filters.submitted_after)
            count_query = count_query.where(TaskRun.submit_time >= filters.submitted_after)

        if filters.submitted_before:
            query = query.where(TaskRun.submit_time <= filters.submitted_before)
            count_query = count_query.where(TaskRun.submit_time <= filters.submitted_before)

        if filters.benchmark_label:
            query = query.join(BenchmarkDefinition).where(
                BenchmarkDefinition.label.ilike(f"%{filters.benchmark_label}%")
            )
            count_query = count_query.join(BenchmarkDefinition).where(
                BenchmarkDefinition.label.ilike(f"%{filters.benchmark_label}%")
            )

        # Get total count
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        # Get paginated results
        query = (
            query.options(selectinload(TaskRun.user))
            .order_by(TaskRun.submit_time.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        task_runs = result.scalars().all()

        return task_runs, total

    async def submit(
        self,
        db: AsyncSession,
        *,
        user: User,
        submission: TaskRunSubmission,
    ) -> tuple[TaskRun, bool]:
        """Process a task run submission from BenchPRO client.

        Handles idempotency, application/benchmark upsert, and atomic transaction.
        Returns tuple of (task_run, is_duplicate).
        """
        task_uuid = submission.client.task_uuid

        # Check for duplicate submission (idempotency)
        existing = await self.get_by_user_and_uuid(db, user.id, task_uuid)
        if existing:
            return existing, True

        # Find or create application
        application_id = None
        if submission.application:
            app_create = ApplicationCreate(
                label=submission.application.label,
                version=submission.application.version,
                system=submission.application.system,
                architecture=submission.application.architecture,
                modules=submission.application.modules,
                benchpro_version=submission.application.benchpro_version,
                build_user=submission.application.build_user,
                build_time=submission.application.build_time,
                extra=submission.application.extra,
            )
            app, _ = await application_service.find_or_create(db, obj_in=app_create)
            application_id = app.id

        # Find or create benchmark definition
        benchmark_id = None
        if submission.benchmark_definition:
            bench_create = BenchmarkDefinitionCreate(
                label=submission.benchmark_definition.label,
                application_id=application_id,
                description=submission.benchmark_definition.description,
                default_primary_fom_name=submission.benchmark_definition.default_primary_fom_name,
                fom_schema=submission.benchmark_definition.fom_schema,
                extra=submission.benchmark_definition.extra,
            )
            bench, _ = await benchmark_definition_service.find_or_create(
                db, obj_in=bench_create
            )
            benchmark_id = bench.id

        # Create task run
        task_run = TaskRun(
            user_id=user.id,
            task_uuid=task_uuid,
            label=submission.task.label,
            benchmark_definition_id=benchmark_id,
            application_id=application_id,
            system=submission.task.system,
            architecture=submission.task.architecture,
            node_count=submission.task.node_count,
            runtime_seconds=submission.task.runtime_seconds,
            status=submission.task.status,
            submit_time=submission.task.submit_time,
            start_time=submission.task.start_time,
            end_time=submission.task.end_time,
            benchpro_version=submission.client.benchpro_version,
            extra=submission.task.extra,
        )
        db.add(task_run)
        await db.flush()  # Get task_run.id

        # Add figures of merit
        if submission.figures_of_merit:
            for fom in submission.figures_of_merit:
                db_fom = FigureOfMerit(
                    task_run_id=task_run.id,
                    name=fom.name,
                    unit=fom.unit,
                    value_numeric=fom.value_numeric,
                    value_text=fom.value_text,
                    value_type=fom.value_type,
                    is_primary=fom.is_primary,
                )
                db.add(db_fom)

        # Add provenance metadata and artifacts
        if submission.provenance:
            if submission.provenance.metadata:
                for meta in submission.provenance.metadata:
                    db_meta = TaskProvenanceMetadata(
                        task_run_id=task_run.id,
                        key=meta.key,
                        value_text=meta.value_text,
                        value_json=meta.value_json,
                    )
                    db.add(db_meta)

            if submission.provenance.artifacts:
                for artifact in submission.provenance.artifacts:
                    db_artifact = ProvenanceArtifact(
                        task_run_id=task_run.id,
                        name=artifact.name,
                        content_type=artifact.content_type,
                        encoding=artifact.encoding,
                        size_bytes=artifact.size_bytes,
                        data=artifact.data,
                    )
                    db.add(db_artifact)

        await db.commit()
        await db.refresh(task_run)

        return task_run, False


# Singleton instance
task_run_service = TaskRunService(TaskRun)

