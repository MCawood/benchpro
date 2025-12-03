"""Benchmark definition endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.benchmark_definition import BenchmarkDefinitionRead
from app.schemas.common import PaginatedResponse
from app.services import benchmark_definition_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[BenchmarkDefinitionRead])
async def list_benchmark_definitions(
    db: DbSession,
    current_user: CurrentUser,
    q: Optional[str] = Query(None, description="Search by label"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[BenchmarkDefinitionRead]:
    """List benchmark definitions with optional search."""
    offset = (page - 1) * per_page

    benchmarks = await benchmark_definition_service.search(
        db, q=q, offset=offset, limit=per_page
    )

    # Get total count (simplified)
    total = await benchmark_definition_service.count(db)

    # Convert to read schemas (application not loaded in search)
    items = []
    for b in benchmarks:
        items.append(BenchmarkDefinitionRead(
            id=b.id,
            label=b.label,
            description=b.description,
            default_primary_fom_name=b.default_primary_fom_name,
            fom_schema=b.fom_schema,
            extra=b.extra,
            application_id=b.application_id,
            application=None,  # Not loaded in list view
            created_at=b.created_at,
            updated_at=b.updated_at,
        ))

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{benchmark_id}", response_model=BenchmarkDefinitionRead)
async def get_benchmark_definition(
    db: DbSession,
    current_user: CurrentUser,
    benchmark_id: int,
) -> BenchmarkDefinitionRead:
    """Get a specific benchmark definition by ID."""
    benchmark = await benchmark_definition_service.get_with_application(db, benchmark_id)

    if not benchmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark definition not found",
        )

    return BenchmarkDefinitionRead.model_validate(benchmark)

