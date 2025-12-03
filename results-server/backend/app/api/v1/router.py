"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1 import (
    api_tokens,
    applications,
    benchmark_definitions,
    health,
    provenance,
    saved_views,
    task_runs,
)

api_router = APIRouter()

# Health check (unauthenticated)
api_router.include_router(health.router, tags=["health"])

# Task runs (submission and queries)
api_router.include_router(
    task_runs.router,
    prefix="/task_runs",
    tags=["task_runs"],
)

# Provenance (uses /task_runs/{id}/provenance and /provenance_artifacts/{id})
api_router.include_router(
    provenance.router,
    tags=["provenance"],
)

# Applications
api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["applications"],
)

# Benchmark definitions
api_router.include_router(
    benchmark_definitions.router,
    prefix="/benchmark_definitions",
    tags=["benchmarks"],
)

# Saved views
api_router.include_router(
    saved_views.router,
    prefix="/saved_views",
    tags=["saved_views"],
)

# API tokens
api_router.include_router(
    api_tokens.router,
    prefix="/api_tokens",
    tags=["tokens"],
)
