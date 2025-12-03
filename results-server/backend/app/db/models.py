"""SQLAlchemy database models.

Schema based on benchpro_results_schema_addendum.txt
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


# Enum types
class UserRole(str, PyEnum):
    USER = "user"
    ADMIN = "admin"


class FomValueType(str, PyEnum):
    NUMERIC = "numeric"
    STRING = "string"


class TaskStatus(str, PyEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SavedViewVisibility(str, PyEnum):
    PRIVATE = "private"
    PUBLIC = "public"


class ArtifactEncoding(str, PyEnum):
    RAW = "raw"
    GZIP = "gzip"


class User(Base):
    """Portal users (from SSO/IdP)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", create_constraint=True),
        nullable=False,
        default=UserRole.USER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    api_tokens: Mapped[list["ApiToken"]] = relationship(
        "ApiToken", back_populates="user", cascade="all, delete-orphan"
    )
    task_runs: Mapped[list["TaskRun"]] = relationship(
        "TaskRun", back_populates="user"
    )
    saved_views: Mapped[list["SavedView"]] = relationship(
        "SavedView", back_populates="owner", cascade="all, delete-orphan"
    )


class ApiToken(Base):
    """Personal access tokens for BenchPRO clients."""

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_tokens")

    __table_args__ = (Index("idx_api_tokens_user_id", "user_id"),)


class Application(Base):
    """Built application instances reused across benchmark runs."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    architecture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    benchpro_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    build_user: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    build_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    benchmark_definitions: Mapped[list["BenchmarkDefinition"]] = relationship(
        "BenchmarkDefinition", back_populates="application"
    )
    task_runs: Mapped[list["TaskRun"]] = relationship(
        "TaskRun", back_populates="application"
    )

    __table_args__ = (
        Index("idx_applications_label", "label"),
        Index("idx_applications_system", "system"),
        Index("idx_applications_architecture", "architecture"),
        Index("idx_applications_label_system_version", "label", "system", "version"),
    )


class BenchmarkDefinition(Base):
    """Conceptual benchmark definition, independent of individual runs."""

    __tablename__ = "benchmark_definitions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    application_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_primary_fom_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fom_schema: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    application: Mapped[Optional["Application"]] = relationship(
        "Application", back_populates="benchmark_definitions"
    )
    task_runs: Mapped[list["TaskRun"]] = relationship(
        "TaskRun", back_populates="benchmark_definition"
    )

    __table_args__ = (Index("idx_benchdefs_app_id", "application_id"),)


class TaskRun(Base):
    """Single execution of a benchmark task."""

    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    task_uuid: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    benchmark_definition_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("benchmark_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    application_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    system: Mapped[str] = mapped_column(Text, nullable=False)
    architecture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    node_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    runtime_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum", create_constraint=True),
        nullable=False,
        default=TaskStatus.COMPLETED,
    )
    submit_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    benchpro_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="task_runs")
    benchmark_definition: Mapped[Optional["BenchmarkDefinition"]] = relationship(
        "BenchmarkDefinition", back_populates="task_runs"
    )
    application: Mapped[Optional["Application"]] = relationship(
        "Application", back_populates="task_runs"
    )
    figures_of_merit: Mapped[list["FigureOfMerit"]] = relationship(
        "FigureOfMerit", back_populates="task_run", cascade="all, delete-orphan"
    )
    provenance_metadata: Mapped[list["TaskProvenanceMetadata"]] = relationship(
        "TaskProvenanceMetadata", back_populates="task_run", cascade="all, delete-orphan"
    )
    provenance_artifacts: Mapped[list["ProvenanceArtifact"]] = relationship(
        "ProvenanceArtifact", back_populates="task_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "task_uuid", name="uq_task_runs_user_taskuuid"),
        Index("idx_task_runs_benchdef_id", "benchmark_definition_id"),
        Index("idx_task_runs_system", "system"),
        Index("idx_task_runs_architecture", "architecture"),
        Index("idx_task_runs_node_count", "node_count"),
        Index("idx_task_runs_submit_time", "submit_time"),
        Index("idx_task_runs_status", "status"),
    )


class FigureOfMerit(Base):
    """FoMs associated with TaskRuns (supports numeric and string values)."""

    __tablename__ = "figures_of_merit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_numeric: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[FomValueType] = mapped_column(
        Enum(FomValueType, name="fom_value_type_enum", create_constraint=True),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    task_run: Mapped["TaskRun"] = relationship(
        "TaskRun", back_populates="figures_of_merit"
    )

    __table_args__ = (
        Index("idx_foms_task_run_id", "task_run_id"),
        Index("idx_foms_name", "name"),
        Index("idx_foms_name_numeric", "name", "value_numeric"),
        Index("idx_foms_name_type", "name", "value_type"),
    )


class TaskProvenanceMetadata(Base):
    """Structured key-value provenance metadata for TaskRuns."""

    __tablename__ = "task_provenance_metadata"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    task_run: Mapped["TaskRun"] = relationship(
        "TaskRun", back_populates="provenance_metadata"
    )

    __table_args__ = (
        Index("idx_task_prov_meta_task_run_id", "task_run_id"),
        Index("idx_task_prov_meta_key", "key"),
    )


class ProvenanceArtifact(Base):
    """Named provenance files associated with TaskRuns."""

    __tablename__ = "provenance_artifacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    encoding: Mapped[ArtifactEncoding] = mapped_column(
        Enum(ArtifactEncoding, name="artifact_encoding_enum", create_constraint=True),
        nullable=False,
        default=ArtifactEncoding.RAW,
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    task_run: Mapped["TaskRun"] = relationship(
        "TaskRun", back_populates="provenance_artifacts"
    )

    __table_args__ = (
        Index("idx_prov_artifacts_task_run_id", "task_run_id"),
        Index("idx_prov_artifacts_name", "name"),
    )


class SavedView(Base):
    """Saved Explorer configurations (filters + table + chart settings)."""

    __tablename__ = "saved_views"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    visibility: Mapped[SavedViewVisibility] = mapped_column(
        Enum(
            SavedViewVisibility,
            name="saved_view_visibility_enum",
            create_constraint=True,
        ),
        nullable=False,
        default=SavedViewVisibility.PRIVATE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="saved_views")

    __table_args__ = (
        Index("idx_saved_views_owner", "owner_user_id"),
        Index("idx_saved_views_visibility", "visibility"),
    )

