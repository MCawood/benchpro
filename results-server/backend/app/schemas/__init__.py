"""Pydantic schemas for request/response validation."""

from app.schemas.api_token import (
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenList,
    ApiTokenRead,
)
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationSummary,
    ApplicationUpdate,
)
from app.schemas.benchmark_definition import (
    BenchmarkDefinitionCreate,
    BenchmarkDefinitionRead,
    BenchmarkDefinitionSummary,
    BenchmarkDefinitionUpdate,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.figure_of_merit import (
    FigureOfMeritCreate,
    FigureOfMeritRead,
    FigureOfMeritSummary,
)
from app.schemas.provenance import (
    ProvenanceArtifactContent,
    ProvenanceArtifactCreate,
    ProvenanceArtifactRead,
    ProvenanceMetadataCreate,
    ProvenanceMetadataRead,
    TaskProvenanceResponse,
)
from app.schemas.saved_view import (
    SavedViewConfig,
    SavedViewCreate,
    SavedViewDetail,
    SavedViewRead,
    SavedViewSummary,
    SavedViewUpdate,
)
from app.schemas.task_run import (
    TaskRunCreate,
    TaskRunDetail,
    TaskRunFilters,
    TaskRunRead,
    TaskRunSubmission,
    TaskRunSubmissionResponse,
    TaskRunSummary,
)
from app.schemas.user import UserCreate, UserRead, UserSummary, UserUpdate

__all__ = [
    # Common
    "ErrorDetail",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationParams",
    # User
    "UserCreate",
    "UserRead",
    "UserSummary",
    "UserUpdate",
    # API Token
    "ApiTokenCreate",
    "ApiTokenCreated",
    "ApiTokenList",
    "ApiTokenRead",
    # Application
    "ApplicationCreate",
    "ApplicationRead",
    "ApplicationSummary",
    "ApplicationUpdate",
    # Benchmark Definition
    "BenchmarkDefinitionCreate",
    "BenchmarkDefinitionRead",
    "BenchmarkDefinitionSummary",
    "BenchmarkDefinitionUpdate",
    # Figure of Merit
    "FigureOfMeritCreate",
    "FigureOfMeritRead",
    "FigureOfMeritSummary",
    # Provenance
    "ProvenanceArtifactContent",
    "ProvenanceArtifactCreate",
    "ProvenanceArtifactRead",
    "ProvenanceMetadataCreate",
    "ProvenanceMetadataRead",
    "TaskProvenanceResponse",
    # Saved View
    "SavedViewConfig",
    "SavedViewCreate",
    "SavedViewDetail",
    "SavedViewRead",
    "SavedViewSummary",
    "SavedViewUpdate",
    # Task Run
    "TaskRunCreate",
    "TaskRunDetail",
    "TaskRunFilters",
    "TaskRunRead",
    "TaskRunSubmission",
    "TaskRunSubmissionResponse",
    "TaskRunSummary",
]
