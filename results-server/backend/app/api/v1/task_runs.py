"""Task run submission and query endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.db.models import TaskStatus, FomValueType
from app.schemas.common import PaginatedResponse
from app.schemas.figure_of_merit import FigureOfMeritSummary
from app.schemas.task_run import (
    TaskRunDetail,
    TaskRunFilters,
    TaskRunSubmission,
    TaskRunSubmissionResponse,
    TaskRunSummary,
)
from app.services import task_run_service

router = APIRouter()


@router.post("", response_model=TaskRunSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_task_run(
    db: DbSession,
    current_user: CurrentUser,
    submission: TaskRunSubmission,
) -> TaskRunSubmissionResponse:
    """Submit a completed task run from BenchPRO client.

    This endpoint is idempotent - submitting the same task_uuid twice
    will return the existing task run without creating a duplicate.
    """
    task_run, is_duplicate = await task_run_service.submit(
        db, user=current_user, submission=submission
    )

    return TaskRunSubmissionResponse(
        status="ok",
        task_run_id=task_run.id,
        duplicate=is_duplicate,
        message="Task run already exists" if is_duplicate else None,
    )


@router.get("", response_model=PaginatedResponse[TaskRunSummary])
async def list_task_runs(
    db: DbSession,
    current_user: CurrentUser,
    # Filter parameters
    system: Optional[list[str]] = Query(None, description="Filter by system(s)"),
    architecture: Optional[str] = Query(None, description="Filter by architecture"),
    benchmark_label: Optional[str] = Query(None, description="Filter by benchmark label"),
    node_count_min: Optional[int] = Query(None, description="Minimum node count"),
    node_count_max: Optional[int] = Query(None, description="Maximum node count"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    submitted_after: Optional[str] = Query(None, description="Filter by submit time (ISO format)"),
    submitted_before: Optional[str] = Query(None, description="Filter by submit time (ISO format)"),
    primary_fom_name: Optional[str] = Query(None, description="Name of primary FoM to include"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[TaskRunSummary]:
    """List task runs with optional filters and pagination."""
    from datetime import datetime

    # Parse datetime filters
    submitted_after_dt = None
    submitted_before_dt = None
    if submitted_after:
        submitted_after_dt = datetime.fromisoformat(submitted_after.replace("Z", "+00:00"))
    if submitted_before:
        submitted_before_dt = datetime.fromisoformat(submitted_before.replace("Z", "+00:00"))

    filters = TaskRunFilters(
        system=system,
        architecture=architecture,
        benchmark_label=benchmark_label,
        node_count_min=node_count_min,
        node_count_max=node_count_max,
        status=status,
        submitted_after=submitted_after_dt,
        submitted_before=submitted_before_dt,
        primary_fom_name=primary_fom_name,
    )

    offset = (page - 1) * per_page
    task_runs, total = await task_run_service.list_with_filters(
        db, filters=filters, offset=offset, limit=per_page
    )

    # Convert to summaries
    summaries = []
    for tr in task_runs:
        # Find primary FoM if requested
        primary_fom = None
        if primary_fom_name and hasattr(tr, "figures_of_merit"):
            for fom in tr.figures_of_merit:
                if fom.name == primary_fom_name:
                    primary_fom = FigureOfMeritSummary.from_read(fom)
                    break

        summary = TaskRunSummary(
            id=tr.id,
            task_uuid=tr.task_uuid,
            label=tr.label,
            system=tr.system,
            architecture=tr.architecture,
            node_count=tr.node_count,
            runtime_seconds=tr.runtime_seconds,
            status=tr.status,
            submit_time=tr.submit_time,
            user=None,  # Could populate if needed
            primary_fom=primary_fom,
        )
        summaries.append(summary)

    return PaginatedResponse.create(
        items=summaries, total=total, page=page, per_page=per_page
    )


@router.get("/{task_run_id}", response_model=TaskRunDetail)
async def get_task_run(
    db: DbSession,
    current_user: CurrentUser,
    task_run_id: int,
) -> TaskRunDetail:
    """Get detailed information about a specific task run."""
    task_run = await task_run_service.get_with_relations(db, task_run_id)

    if not task_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task run not found",
        )

    # Build FoM summaries
    fom_summaries = []
    for fom in task_run.figures_of_merit:
        fom_summaries.append(
            FigureOfMeritSummary(
                name=fom.name,
                value=fom.value_numeric if fom.value_type == FomValueType.NUMERIC else fom.value_text,
                unit=fom.unit,
                value_type=fom.value_type,
                is_primary=fom.is_primary,
            )
        )

    return TaskRunDetail(
        id=task_run.id,
        user_id=task_run.user_id,
        task_uuid=task_run.task_uuid,
        label=task_run.label,
        benchmark_definition_id=task_run.benchmark_definition_id,
        application_id=task_run.application_id,
        system=task_run.system,
        architecture=task_run.architecture,
        node_count=task_run.node_count,
        runtime_seconds=task_run.runtime_seconds,
        status=task_run.status,
        submit_time=task_run.submit_time,
        start_time=task_run.start_time,
        end_time=task_run.end_time,
        benchpro_version=task_run.benchpro_version,
        extra=task_run.extra,
        created_at=task_run.created_at,
        updated_at=task_run.updated_at,
        user=None,  # Could populate
        application=None,  # Could populate
        benchmark_definition=None,  # Could populate
        figures_of_merit=fom_summaries,
    )

