# BenchPRO Results Server - Schema Reference

**For Developers and LLMs**

This document provides a complete reference for the database schema, data models, and relationships in the BenchPRO Results Server.

---

## Table of Contents

1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Core Entities](#core-entities)
4. [Enum Types](#enum-types)
5. [Indexes](#indexes)
6. [SQLAlchemy Models](#sqlalchemy-models)
7. [Pydantic Schemas](#pydantic-schemas)
8. [Common Patterns](#common-patterns)

---

## Overview

The BenchPRO Results Server uses PostgreSQL 15+ with the following characteristics:

- **Primary Keys**: `BIGSERIAL` (auto-incrementing 64-bit integers)
- **Timestamps**: `TIMESTAMPTZ` with automatic `created_at` and `updated_at`
- **JSON Storage**: `JSONB` for flexible metadata
- **Enums**: PostgreSQL native enum types for constrained values
- **Text Fields**: `VARCHAR` with no length limits (PostgreSQL optimizes automatically)

### Schema Version

Managed by Alembic migrations. Current revision stored in `alembic_version` table.

---

## Entity Relationship Diagram

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │◄─────────────────────────────────────────────────┐
│ external_id     │                                                  │
│ display_name    │                                                  │
│ email           │                                                  │
│ role            │                                                  │
│ created_at      │                                                  │
│ updated_at      │                                                  │
└────────┬────────┘                                                  │
         │                                                           │
         │ 1:N                                                       │
         ▼                                                           │
┌─────────────────┐                                                  │
│   api_tokens    │                                                  │
├─────────────────┤                                                  │
│ id (PK)         │                                                  │
│ user_id (FK)    │──────────────────────────────────────────────────┤
│ name            │                                                  │
│ token_hash      │                                                  │
│ last_used_at    │                                                  │
│ revoked_at      │                                                  │
│ created_at      │                                                  │
└─────────────────┘                                                  │
                                                                     │
┌─────────────────┐       ┌─────────────────────┐                    │
│  applications   │       │ benchmark_definitions│                   │
├─────────────────┤       ├─────────────────────┤                    │
│ id (PK)         │◄──┐   │ id (PK)             │◄──┐                │
│ label           │   │   │ label               │   │                │
│ version         │   │   │ application_id (FK) │───┘ (optional)     │
│ system          │   │   │ description         │                    │
│ architecture    │   │   │ default_primary_fom │                    │
│ modules (JSONB) │   │   │ created_at          │                    │
│ build_user      │   │   │ updated_at          │                    │
│ build_time      │   │   └──────────┬──────────┘                    │
│ benchpro_version│   │              │                               │
│ extra (JSONB)   │   │              │ 1:N                           │
│ created_at      │   │              │                               │
│ updated_at      │   │              │                               │
└─────────────────┘   │              │                               │
                      │              │                               │
                      │              ▼                               │
                      │   ┌─────────────────────┐                    │
                      │   │     task_runs       │                    │
                      │   ├─────────────────────┤                    │
                      │   │ id (PK)             │◄───────────────────┤
                      │   │ user_id (FK)        │────────────────────┘
                      └───│ application_id (FK) │
                          │ benchmark_def_id(FK)│
                          │ task_uuid (UNIQUE)  │
                          │ label               │
                          │ system              │
                          │ architecture        │
                          │ node_count          │
                          │ runtime_seconds     │
                          │ status              │
                          │ submit_time         │
                          │ start_time          │
                          │ end_time            │
                          │ benchpro_version    │
                          │ extra (JSONB)       │
                          │ created_at          │
                          │ updated_at          │
                          └──────────┬──────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │ 1:N                  │ 1:N                  │ 1:N
              ▼                      ▼                      ▼
┌─────────────────────┐  ┌───────────────────────┐  ┌────────────────────┐
│ figures_of_merit    │  │task_provenance_metadata│  │provenance_artifacts│
├─────────────────────┤  ├───────────────────────┤  ├────────────────────┤
│ id (PK)             │  │ id (PK)               │  │ id (PK)            │
│ task_run_id (FK)    │  │ task_run_id (FK)      │  │ task_run_id (FK)   │
│ name                │  │ key                   │  │ name               │
│ value_numeric       │  │ value_text            │  │ content_type       │
│ value_text          │  │ value_json (JSONB)    │  │ encoding           │
│ value_type          │  │ created_at            │  │ size_bytes         │
│ unit                │  │ updated_at            │  │ data (BYTEA)       │
│ is_primary          │  └───────────────────────┘  │ created_at         │
│ extra (JSONB)       │                             └────────────────────┘
│ created_at          │
│ updated_at          │
└─────────────────────┘

┌─────────────────────┐
│    saved_views      │
├─────────────────────┤
│ id (PK)             │
│ owner_user_id (FK)  │───► users.id
│ name                │
│ description         │
│ config (JSONB)      │
│ visibility          │
│ created_at          │
│ updated_at          │
└─────────────────────┘
```

---

## Core Entities

### users

Stores user accounts, typically synchronized from SSO/OIDC.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `external_id` | `VARCHAR` | UNIQUE, NOT NULL | SSO/OIDC subject identifier |
| `display_name` | `VARCHAR` | | Human-readable name |
| `email` | `VARCHAR` | | User email address |
| `role` | `user_role_enum` | NOT NULL, DEFAULT 'USER' | User role (USER, ADMIN) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Last update timestamp |

### api_tokens

Personal Access Tokens for API authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `user_id` | `BIGINT` | FK → users.id, NOT NULL | Token owner |
| `name` | `VARCHAR` | NOT NULL | User-provided token name |
| `token_hash` | `VARCHAR` | NOT NULL | Argon2 hash of token |
| `last_used_at` | `TIMESTAMPTZ` | | Last API call timestamp |
| `revoked_at` | `TIMESTAMPTZ` | | Revocation timestamp (null = active) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |

### applications

Built software applications used in benchmarks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `label` | `VARCHAR` | NOT NULL | Application name (e.g., "lammps") |
| `version` | `VARCHAR` | | Version string (e.g., "23Jun2022") |
| `system` | `VARCHAR` | | HPC system where built |
| `architecture` | `VARCHAR` | | CPU architecture (e.g., "intel_spr") |
| `modules` | `JSONB` | | Module list as JSON array |
| `build_user` | `VARCHAR` | | Username who built it |
| `build_time` | `TIMESTAMPTZ` | | When it was built |
| `benchpro_version` | `VARCHAR` | | BenchPRO version used |
| `extra` | `JSONB` | | Additional metadata |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Last update timestamp |

**Unique Constraint**: `(label, version, system, architecture)`

### benchmark_definitions

Defines benchmark types and their expected metrics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `label` | `VARCHAR` | UNIQUE, NOT NULL | Benchmark identifier |
| `application_id` | `BIGINT` | FK → applications.id | Associated application (optional) |
| `description` | `VARCHAR` | | Human-readable description |
| `default_primary_fom_name` | `VARCHAR` | | Name of primary figure of merit |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Last update timestamp |

### task_runs

Individual benchmark execution records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `user_id` | `BIGINT` | FK → users.id, NOT NULL | Submitting user |
| `task_uuid` | `UUID` | UNIQUE, NOT NULL | Client-generated unique ID |
| `label` | `VARCHAR` | NOT NULL | Task label/name |
| `benchmark_definition_id` | `BIGINT` | FK → benchmark_definitions.id | Benchmark type |
| `application_id` | `BIGINT` | FK → applications.id | Application used |
| `system` | `VARCHAR` | NOT NULL | HPC system name |
| `architecture` | `VARCHAR` | | CPU architecture |
| `node_count` | `INTEGER` | | Number of compute nodes |
| `runtime_seconds` | `FLOAT` | | Total execution time |
| `status` | `task_status_enum` | NOT NULL | Completion status |
| `submit_time` | `TIMESTAMPTZ` | NOT NULL | Job submission time |
| `start_time` | `TIMESTAMPTZ` | | Job start time |
| `end_time` | `TIMESTAMPTZ` | | Job completion time |
| `benchpro_version` | `VARCHAR` | | BenchPRO version used |
| `extra` | `JSONB` | | Additional metadata |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Record creation time |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Last update timestamp |

### figures_of_merit

Performance metrics captured from benchmark runs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `task_run_id` | `BIGINT` | FK → task_runs.id, NOT NULL | Parent task run |
| `name` | `VARCHAR` | NOT NULL | Metric name (e.g., "gflops") |
| `value_numeric` | `DOUBLE PRECISION` | | Numeric value |
| `value_text` | `VARCHAR` | | Text value (for non-numeric metrics) |
| `value_type` | `fom_value_type_enum` | NOT NULL | NUMERIC or STRING |
| `unit` | `VARCHAR` | | Unit of measurement |
| `is_primary` | `BOOLEAN` | NOT NULL, DEFAULT false | Is this the primary metric? |
| `extra` | `JSONB` | | Additional metadata |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Last update timestamp |

### task_provenance_metadata

Key-value metadata for reproducibility.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `task_run_id` | `BIGINT` | FK → task_runs.id, NOT NULL | Parent task run |
| `key` | `VARCHAR` | NOT NULL | Metadata key |
| `value_text` | `VARCHAR` | | Simple text value |
| `value_json` | `JSONB` | | Complex JSON value |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Last update timestamp |

**Unique Constraint**: `(task_run_id, key)`

### provenance_artifacts

Binary or text files captured from benchmark runs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `task_run_id` | `BIGINT` | FK → task_runs.id, NOT NULL | Parent task run |
| `name` | `VARCHAR` | NOT NULL | Artifact name (e.g., "stdout") |
| `content_type` | `VARCHAR` | NOT NULL | MIME type (e.g., "text/plain") |
| `encoding` | `artifact_encoding_enum` | NOT NULL, DEFAULT 'raw' | Compression encoding |
| `size_bytes` | `BIGINT` | NOT NULL | Size in bytes |
| `data` | `BYTEA` | NOT NULL | Raw binary data |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |

### saved_views

User-created filter presets.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Auto-incrementing ID |
| `owner_user_id` | `BIGINT` | FK → users.id, NOT NULL | View owner |
| `name` | `VARCHAR` | NOT NULL | View name |
| `description` | `VARCHAR` | | View description |
| `config` | `JSONB` | NOT NULL | Filter configuration |
| `visibility` | `saved_view_visibility_enum` | NOT NULL, DEFAULT 'private' | Access level |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Last update timestamp |

---

## Enum Types

### user_role_enum

```sql
CREATE TYPE user_role_enum AS ENUM ('USER', 'ADMIN');
```

| Value | Description |
|-------|-------------|
| `USER` | Standard user with read/write access to own data |
| `ADMIN` | Administrator with full access |

### task_status_enum

```sql
CREATE TYPE task_status_enum AS ENUM ('pending', 'running', 'completed', 'failed', 'partial', 'cancelled');
```

| Value | Description |
|-------|-------------|
| `pending` | Task submitted but not started |
| `running` | Task currently executing |
| `completed` | Task finished successfully |
| `failed` | Task encountered an error |
| `partial` | Task completed with partial results |
| `cancelled` | Task was cancelled |

### fom_value_type_enum

```sql
CREATE TYPE fom_value_type_enum AS ENUM ('numeric', 'string');
```

| Value | Description |
|-------|-------------|
| `numeric` | Value stored in `value_numeric` (DOUBLE PRECISION) |
| `string` | Value stored in `value_text` (VARCHAR) |

### artifact_encoding_enum

```sql
CREATE TYPE artifact_encoding_enum AS ENUM ('raw', 'gzip', 'base64');
```

| Value | Description |
|-------|-------------|
| `raw` | Uncompressed binary data |
| `gzip` | Gzip-compressed data |
| `base64` | Base64-encoded data |

### saved_view_visibility_enum

```sql
CREATE TYPE saved_view_visibility_enum AS ENUM ('private', 'public');
```

| Value | Description |
|-------|-------------|
| `private` | Only visible to owner |
| `public` | Visible to all authenticated users |

---

## Indexes

### Primary Indexes (automatic)

All tables have a primary key index on `id`.

### Unique Indexes

```sql
-- users
CREATE UNIQUE INDEX ix_users_external_id ON users(external_id);

-- applications (composite)
CREATE UNIQUE INDEX ix_applications_unique 
  ON applications(label, version, system, architecture);

-- benchmark_definitions
CREATE UNIQUE INDEX ix_benchmark_definitions_label ON benchmark_definitions(label);

-- task_runs
CREATE UNIQUE INDEX ix_task_runs_task_uuid ON task_runs(task_uuid);

-- task_provenance_metadata (composite)
CREATE UNIQUE INDEX ix_provenance_metadata_unique 
  ON task_provenance_metadata(task_run_id, key);
```

### Query Performance Indexes

```sql
-- Task runs: common filter columns
CREATE INDEX ix_task_runs_system ON task_runs(system);
CREATE INDEX ix_task_runs_status ON task_runs(status);
CREATE INDEX ix_task_runs_submit_time ON task_runs(submit_time);
CREATE INDEX ix_task_runs_user_id ON task_runs(user_id);
CREATE INDEX ix_task_runs_benchmark_definition_id ON task_runs(benchmark_definition_id);

-- Figures of merit: lookup by task
CREATE INDEX ix_figures_of_merit_task_run_id ON figures_of_merit(task_run_id);
CREATE INDEX ix_figures_of_merit_name ON figures_of_merit(name);

-- Provenance: lookup by task
CREATE INDEX ix_provenance_metadata_task_run_id ON task_provenance_metadata(task_run_id);
CREATE INDEX ix_provenance_artifacts_task_run_id ON provenance_artifacts(task_run_id);

-- Saved views: user lookup
CREATE INDEX ix_saved_views_owner_user_id ON saved_views(owner_user_id);
```

---

## SQLAlchemy Models

Located in `backend/app/db/models.py`:

```python
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    external_id = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    email = Column(String)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    api_tokens = relationship("ApiToken", back_populates="user")
    task_runs = relationship("TaskRun", back_populates="user")
    saved_views = relationship("SavedView", back_populates="owner")

class TaskRun(Base):
    __tablename__ = "task_runs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    task_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False)
    label = Column(String, nullable=False)
    # ... additional columns ...
    
    # Relationships
    user = relationship("User", back_populates="task_runs")
    figures_of_merit = relationship("FigureOfMerit", back_populates="task_run")
    provenance_metadata = relationship("TaskProvenanceMetadata", back_populates="task_run")
    provenance_artifacts = relationship("ProvenanceArtifact", back_populates="task_run")
```

---

## Pydantic Schemas

Located in `backend/app/schemas/`:

### Naming Conventions

| Suffix | Purpose | Example |
|--------|---------|---------|
| `Base` | Shared fields | `TaskRunBase` |
| `Create` | POST request body | `TaskRunCreate` |
| `Update` | PUT/PATCH request body | `TaskRunUpdate` |
| `Read` | GET response with all fields | `TaskRunRead` |
| `Summary` | Abbreviated response | `TaskRunSummary` |

### Example Schema

```python
# app/schemas/task_run.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class TaskRunBase(BaseModel):
    label: str
    system: str
    architecture: Optional[str] = None
    node_count: Optional[int] = None

class TaskRunCreate(TaskRunBase):
    task_uuid: UUID
    status: TaskStatus
    submit_time: datetime

class TaskRunRead(TaskRunBase):
    id: int
    user_id: int
    task_uuid: UUID
    status: TaskStatus
    submit_time: datetime
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TaskRunSummary(BaseModel):
    id: int
    label: str
    system: str
    node_count: Optional[int]
    status: TaskStatus
    submit_time: datetime
```

---

## Common Patterns

### Timestamps

All tables include automatic timestamps:

```python
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

### Soft Deletes

Currently not implemented. To add:

```python
deleted_at = Column(DateTime(timezone=True), nullable=True)
```

### JSONB Fields

Used for flexible metadata:

```python
extra = Column(JSONB, default={})
modules = Column(JSONB, default=[])
config = Column(JSONB, nullable=False)
```

Query JSONB in SQLAlchemy:

```python
# Filter by JSON field
stmt = select(TaskRun).where(TaskRun.extra['custom_field'].astext == 'value')

# Filter by JSON array contains
from sqlalchemy.dialects.postgresql import JSONB
stmt = select(Application).where(Application.modules.contains(['intel/23.1']))
```

### Idempotent Upserts

For task submissions with duplicate detection:

```python
async def submit(self, db: AsyncSession, submission: TaskRunSubmission):
    # Check for existing
    existing = await db.execute(
        select(TaskRun).where(TaskRun.task_uuid == submission.client.task_uuid)
    )
    if existing.scalar_one_or_none():
        return existing, True  # Duplicate
    
    # Create new
    task_run = TaskRun(**submission.dict())
    db.add(task_run)
    await db.commit()
    return task_run, False
```

---

## Migration Example

Creating a new migration after model changes:

```bash
cd backend
source venv/bin/activate

# Auto-generate migration
alembic revision --autogenerate -m "Add new_column to task_runs"

# Review the generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

Generated migration structure:

```python
# alembic/versions/xxxx_add_new_column.py

def upgrade():
    op.add_column('task_runs', 
        sa.Column('new_column', sa.String(), nullable=True)
    )
    op.create_index('ix_task_runs_new_column', 'task_runs', ['new_column'])

def downgrade():
    op.drop_index('ix_task_runs_new_column')
    op.drop_column('task_runs', 'new_column')
```

