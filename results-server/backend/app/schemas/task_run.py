"""TaskRun Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.db.models import TaskStatus
from app.schemas.application import ApplicationSummary
from app.schemas.benchmark_definition import BenchmarkDefinitionSummary
from app.schemas.common import BaseSchema, TimestampMixin
from app.schemas.figure_of_merit import FigureOfMeritCreate, FigureOfMeritSummary
from app.schemas.provenance import ProvenanceArtifactCreate, ProvenanceMetadataCreate
from app.schemas.user import UserSummary


# --- Task Run Core Schemas ---


class TaskRunBase(BaseSchema):
    """Base task run schema."""

    label: str
    system: str
    architecture: Optional[str] = None
    node_count: Optional[int] = None
    runtime_seconds: Optional[float] = None
    status: TaskStatus = TaskStatus.COMPLETED
    submit_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    benchpro_version: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class TaskRunCreate(TaskRunBase):
    """Schema for creating a task run directly."""

    task_uuid: UUID
    benchmark_definition_id: Optional[int] = None
    application_id: Optional[int] = None


# --- Task Run Submission (from BenchPRO client) ---


class ClientInfo(BaseSchema):
    """Client information in submission."""

    benchpro_version: str
    task_uuid: UUID


class ApplicationSubmission(BaseSchema):
    """Application info in task submission."""

    label: str
    version: Optional[str] = None
    system: Optional[str] = None
    architecture: Optional[str] = None
    modules: Optional[list[str]] = None
    benchpro_version: Optional[str] = None
    build_user: Optional[str] = None
    build_time: Optional[datetime] = None
    extra: Optional[dict[str, Any]] = None


class BenchmarkSubmission(BaseSchema):
    """Benchmark definition info in task submission."""

    label: str
    description: Optional[str] = None
    default_primary_fom_name: Optional[str] = None
    fom_schema: Optional[dict[str, Any]] = None
    extra: Optional[dict[str, Any]] = None


class TaskSubmission(BaseSchema):
    """Task info in submission."""

    label: str
    system: str
    architecture: Optional[str] = None
    node_count: Optional[int] = None
    runtime_seconds: Optional[float] = None
    status: TaskStatus = TaskStatus.COMPLETED
    submit_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    extra: Optional[dict[str, Any]] = None


class ProvenanceSubmission(BaseSchema):
    """Provenance data in task submission."""

    metadata: Optional[list[ProvenanceMetadataCreate]] = None
    artifacts: Optional[list[ProvenanceArtifactCreate]] = None


class TaskRunSubmission(BaseSchema):
    """Complete task run submission from BenchPRO client.

    This is the payload sent to POST /api/v1/task_runs
    """

    client: ClientInfo
    task: TaskSubmission
    application: Optional[ApplicationSubmission] = None
    benchmark_definition: Optional[BenchmarkSubmission] = None
    figures_of_merit: Optional[list[FigureOfMeritCreate]] = None
    provenance: Optional[ProvenanceSubmission] = None


class TaskRunSubmissionResponse(BaseSchema):
    """Response after successful task submission."""

    status: str = "ok"
    task_run_id: int
    duplicate: bool = False
    message: Optional[str] = None


# --- Task Run Read Schemas ---


class TaskRunRead(TaskRunBase, TimestampMixin):
    """Schema for reading task run data."""

    id: int
    user_id: int
    task_uuid: UUID
    benchmark_definition_id: Optional[int] = None
    application_id: Optional[int] = None


class TaskRunSummary(BaseSchema):
    """Summarized task run for list views."""

    id: int
    task_uuid: UUID
    label: str
    system: str
    architecture: Optional[str] = None
    node_count: Optional[int] = None
    runtime_seconds: Optional[float] = None
    status: TaskStatus
    submit_time: datetime
    user: Optional[UserSummary] = None
    primary_fom: Optional[FigureOfMeritSummary] = None


class TaskRunDetail(TaskRunRead):
    """Detailed task run with related entities."""

    user: Optional[UserSummary] = None
    application: Optional[ApplicationSummary] = None
    benchmark_definition: Optional[BenchmarkDefinitionSummary] = None
    figures_of_merit: list[FigureOfMeritSummary] = []


# --- Task Run Query Filters ---


class TaskRunFilters(BaseSchema):
    """Query filters for task runs."""

    system: Optional[list[str]] = None
    architecture: Optional[str] = None
    benchmark_label: Optional[str] = None
    node_count_min: Optional[int] = None
    node_count_max: Optional[int] = None
    status: Optional[TaskStatus] = None
    user: Optional[str] = None
    submitted_after: Optional[datetime] = None
    submitted_before: Optional[datetime] = None
    primary_fom_name: Optional[str] = None

