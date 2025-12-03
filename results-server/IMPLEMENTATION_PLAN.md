# BenchPRO Results Collection Backend - Implementation Plan

**Version:** 1.0  
**Date:** December 1, 2025  
**Status:** ✅ MVP COMPLETE

---

## 1. Overview

This document outlines the implementation plan for the BenchPRO Results Collection & Visualization Component. This system provides:

- A **Python backend** (FastAPI) serving REST APIs for task submission, queries, and authentication
- A **PostgreSQL database** for storing benchmark results and provenance
- A **SvelteKit web portal** for exploring results, visualizing Figures of Merit (FoMs), and managing saved views

The implementation follows the requirements defined in:
- `benchpro_results_prd.txt` - Product Requirements Document
- `benchpro_results_schema_addendum.txt` - PostgreSQL Schema Definition

---

## 2. Project Structure

```
results-server/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/          # Versioned API routes
│   │   │       ├── __init__.py
│   │   │       ├── health.py
│   │   │       ├── task_runs.py
│   │   │       ├── provenance.py
│   │   │       ├── applications.py
│   │   │       ├── benchmark_definitions.py
│   │   │       ├── saved_views.py
│   │   │       └── api_tokens.py
│   │   ├── core/            # Configuration, security, dependencies
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── db/              # Database models and session
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models.py
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── task_run.py
│   │   │   ├── application.py
│   │   │   ├── benchmark_definition.py
│   │   │   ├── figure_of_merit.py
│   │   │   ├── provenance.py
│   │   │   ├── saved_view.py
│   │   │   ├── user.py
│   │   │   └── api_token.py
│   │   ├── services/        # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── task_run.py
│   │   │   ├── provenance.py
│   │   │   └── saved_view.py
│   │   └── main.py          # FastAPI application entry point
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── alembic/             # Database migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── pyproject.toml
│   └── requirements.txt
│
├── frontend/                # SvelteKit web portal
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   ├── stores/
│   │   │   └── api/
│   │   ├── routes/
│   │   │   ├── +layout.svelte
│   │   │   ├── +page.svelte
│   │   │   ├── explorer/
│   │   │   ├── task/[id]/
│   │   │   ├── saved-views/
│   │   │   └── settings/
│   │   └── app.html
│   ├── static/
│   ├── package.json
│   ├── svelte.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── docker-compose.yaml      # PostgreSQL + dev services
├── seed/                    # Seed data scripts
│   └── seed_data.py
├── .env.example
├── IMPLEMENTATION_PLAN.md
└── README.md
```

---

## 3. Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Backend Framework | FastAPI | 0.109+ |
| Python | Python | 3.11+ |
| ORM | SQLAlchemy | 2.0+ (async) |
| Database | PostgreSQL | 15+ |
| DB Driver | asyncpg | 0.29+ |
| Migrations | Alembic | 1.13+ |
| Password Hashing | passlib[argon2] | 1.7+ |
| JWT | python-jose | 3.3+ |
| Validation | Pydantic | 2.5+ |
| HTTP Client | httpx | 0.26+ |
| Frontend | SvelteKit | 2.0+ |
| CSS | TailwindCSS | 3.4+ |
| Charts | ECharts | 5.4+ |
| Dev Infrastructure | Docker Compose | 2.0+ |

---

## 4. Implementation Phases

### Phase 1: Foundation & Infrastructure ✅ COMPLETE

**Goal:** Set up project structure, database, and core configuration.

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Create `results-server/` directory structure | ✅ Done |
| 1.2 | Write IMPLEMENTATION_PLAN.md | ✅ Done |
| 1.3 | Set up Python venv with FastAPI, SQLAlchemy, asyncpg, Alembic | ✅ Done |
| 1.4 | Create `docker-compose.yaml` for PostgreSQL | ✅ Done |
| 1.5 | Set up Alembic migrations with initial schema | ✅ Done |
| 1.6 | Create core configuration (env vars, database DSN) | ✅ Done |
| 1.7 | Create FastAPI app entry point with health endpoint | ✅ Done |

**Completed:** December 1, 2025

---

### Phase 2: Database Models & Core API ✅ COMPLETE

**Goal:** Define all database models and basic CRUD operations.

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | Define SQLAlchemy models for all entities | ✅ Done |
| 2.2 | Create Pydantic schemas for request/response validation | ✅ Done |
| 2.3 | Implement database session management | ✅ Done |
| 2.4 | Implement basic CRUD services layer | ✅ Done |
| 2.5 | Create security module (JWT, Argon2 hashing) | ✅ Done |
| 2.6 | Create authentication dependencies | ✅ Done |

**Completed:** December 1, 2025

**Entities:**
- `users`
- `api_tokens`
- `applications`
- `benchmark_definitions`
- `task_runs`
- `figures_of_merit`
- `task_provenance_metadata`
- `provenance_artifacts`
- `saved_views`

---

### Phase 3: Authentication & Security ✅ COMPLETE

**Goal:** Implement PAT and SSO authentication, authorization.

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | PAT authentication middleware (Bearer token) | ✅ Done |
| 3.2 | Password hashing with Argon2 | ✅ Done |
| 3.3 | API token management endpoints | ✅ Done |
| 3.4 | SSO/OIDC integration (mock mode for local dev) | ✅ Done |
| 3.5 | User creation on first login | ✅ Done |
| 3.6 | Role-based authorization (user/admin) | ✅ Done |

**Completed:** December 1, 2025

---

### Phase 4: Task Submission Pipeline (MVP Critical) ✅ COMPLETE

**Goal:** Implement the core task submission endpoint.

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Define `TaskRunSubmission` Pydantic schema | ✅ Done |
| 4.2 | Implement `POST /api/v1/task_runs` endpoint | ✅ Done |
| 4.3 | Atomic transaction handling | ✅ Done |
| 4.4 | Idempotency via `(user_id, task_uuid)` | ✅ Done |
| 4.5 | Application/BenchmarkDefinition upsert logic | ✅ Done |
| 4.6 | FoM storage (numeric/string handling) | ✅ Done |
| 4.7 | Provenance metadata and artifact storage | ✅ Done |
| 4.8 | Validation and structured error responses | ✅ Done |
| 4.9 | Basic rate limiting | ⏳ Deferred |

**Completed:** December 1, 2025

**Key Requirements:**
- All inserts within single transaction (atomic)
- Retry-safe via idempotency key
- Validation errors return HTTP 400 with details
- Artifacts stored compressed (gzip optional)

---

### Phase 5: Query APIs ✅ COMPLETE

**Goal:** Implement endpoints for querying results and provenance.

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | `GET /api/v1/task_runs` with filters and pagination | ✅ Done |
| 5.2 | `GET /api/v1/task_runs/{id}` with full details | ✅ Done |
| 5.3 | `GET /api/v1/task_runs/{id}/provenance` | ✅ Done |
| 5.4 | `GET /api/v1/provenance_artifacts/{id}` (text/raw) | ✅ Done |
| 5.5 | `GET /api/v1/benchmark_definitions` | ✅ Done |
| 5.6 | `GET /api/v1/applications` | ✅ Done |

**Completed:** December 1, 2025

**Filter Parameters for task_runs:**
- `system` (multi-select)
- `architecture`
- `benchmark_label`
- `node_count_min`, `node_count_max`
- `submitted_after`, `submitted_before`
- `status`
- `user`
- `primary_fom_name`
- `page`, `per_page`

---

### Phase 6: Saved Views API ✅ COMPLETE

**Goal:** Implement saved view management.

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | `GET /api/v1/saved_views` (mine/shared/all) | ✅ Done |
| 6.2 | `POST /api/v1/saved_views` | ✅ Done |
| 6.3 | `GET /api/v1/saved_views/{id}` | ✅ Done |
| 6.4 | `PUT /api/v1/saved_views/{id}` | ✅ Done |
| 6.5 | `DELETE /api/v1/saved_views/{id}` | ✅ Done |
| 6.6 | Visibility handling (private/public) | ✅ Done |

**Completed:** December 1, 2025

---

### Phase 7: Frontend - SvelteKit Setup ✅ COMPLETE

**Goal:** Initialize the web portal with core infrastructure.

| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Initialize SvelteKit project | ✅ Done |
| 7.2 | Configure TailwindCSS | ✅ Done |
| 7.3 | Set up API client utilities | ✅ Done |
| 7.4 | Auth flow (mock SSO for local dev) | ✅ Done (dev mode) |
| 7.5 | Layout and navigation components | ✅ Done |
| 7.6 | Theme and styling system | ✅ Done |

**Completed:** December 1, 2025

---

### Phase 8: Frontend - Results Explorer (MVP Critical) ✅ COMPLETE

**Goal:** Build the primary UI for browsing results.

| Task | Description | Status |
|------|-------------|--------|
| 8.1 | Filter panel component | ✅ Done |
| 8.2 | Data table with sorting and pagination | ✅ Done |
| 8.3 | FoM selection dropdown | ⏳ Deferred |
| 8.4 | CSV export functionality | ✅ Done |
| 8.5 | Chart view (line, scatter, bar) | ✅ Done |
| 8.6 | Animated chart transitions | ✅ Done (ECharts) |
| 8.7 | Table/Chart view toggle | ✅ Done |

**Completed:** December 1, 2025

---

### Phase 9: Frontend - Task Detail & Provenance ✅ COMPLETE

**Goal:** Build detailed task view with provenance inspection.

| Task | Description | Status |
|------|-------------|--------|
| 9.1 | Task summary section | ✅ Done |
| 9.2 | FoMs table with primary highlight | ✅ Done |
| 9.3 | Provenance tab layout | ✅ Done |
| 9.4 | Artifact listing component | ✅ Done |
| 9.5 | Inline text viewer (stdout, modules) | ✅ Done |
| 9.6 | Artifact download functionality | ⏳ Deferred |
| 9.7 | Structured provenance display (scheduler, env) | ✅ Done |

**Completed:** December 1, 2025

---

### Phase 10: Frontend - User Features ✅ COMPLETE

**Goal:** Implement user management features.

| Task | Description | Status |
|------|-------------|--------|
| 10.1 | PAT management page | ✅ Done |
| 10.2 | Saved views list page | ✅ Done |
| 10.3 | Save current view dialog | ⏳ Deferred |
| 10.4 | Load saved view | ⏳ Deferred |
| 10.5 | Profile/settings page | ✅ Done |

**Completed:** December 1, 2025

---

### Phase 11: Testing & Polish ✅ COMPLETE

**Goal:** Ensure quality and developer experience.

| Task | Description | Status |
|------|-------------|--------|
| 11.1 | Unit tests for submission mapping | ✅ Done |
| 11.2 | Unit tests for FoM handling | ✅ Done |
| 11.3 | Integration tests (submit → query) | ✅ Done |
| 11.4 | Saved views lifecycle tests | ✅ Done |
| 11.5 | Seed data generation script | ✅ Done |
| 11.6 | API documentation (OpenAPI) | ✅ Done (auto-generated) |
| 11.7 | README with setup instructions | ✅ Done |
| 11.8 | Frontend smoke tests | ⏳ Deferred |

**Completed:** December 1, 2025

---

## 5. API Endpoints Summary

### Health
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Server status and version |

### Task Submission
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/task_runs` | PAT | Submit a completed task |

### Task Queries
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/task_runs` | Yes | List/filter task runs |
| GET | `/api/v1/task_runs/{id}` | Yes | Get task run details |
| GET | `/api/v1/task_runs/{id}/provenance` | Yes | Get provenance metadata |
| GET | `/api/v1/provenance_artifacts/{id}` | Yes | Get artifact content |

### Metadata
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/benchmark_definitions` | Yes | List benchmark definitions |
| GET | `/api/v1/applications` | Yes | List applications |

### Saved Views
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/saved_views` | Yes | List saved views |
| POST | `/api/v1/saved_views` | Yes | Create saved view |
| GET | `/api/v1/saved_views/{id}` | Yes | Get saved view |
| PUT | `/api/v1/saved_views/{id}` | Yes | Update saved view |
| DELETE | `/api/v1/saved_views/{id}` | Yes | Delete saved view |

### API Tokens
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/api_tokens` | Yes | List user's tokens |
| POST | `/api/v1/api_tokens` | Yes | Create new token |
| DELETE | `/api/v1/api_tokens/{id}` | Yes | Revoke token |

---

## 6. Database Schema Summary

See `benchpro_results_schema_addendum.txt` for full schema. Core tables:

- **users** - Portal users (SSO-linked)
- **api_tokens** - Personal access tokens for API auth
- **applications** - Built application instances
- **benchmark_definitions** - Benchmark configurations
- **task_runs** - Individual benchmark executions
- **figures_of_merit** - Numeric/string FoMs per task
- **task_provenance_metadata** - Key-value provenance data
- **provenance_artifacts** - Binary provenance files (stdout, logs)
- **saved_views** - Saved explorer configurations

---

## 7. Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

### Quick Start
```bash
# Start PostgreSQL
cd results-server
docker-compose up -d postgres

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables
See `.env.example` for required configuration:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key
- `OIDC_*` - SSO configuration (optional for local dev)

---

## 8. Non-Functional Requirements

### Performance
- API queries: 95th percentile ≤ 1 second
- Task submission (≤10MB): 95th percentile ≤ 3 seconds
- Charts: Render up to 1,000 points without lag

### Security
- All endpoints (except health) require authentication
- PATs stored as Argon2 hashes only
- Parameterized queries (no SQL injection)
- HTTPS in production

### Reliability
- Task submissions are atomic (all-or-nothing)
- Idempotent via `(user_id, task_uuid)`
- Safe to retry on failure

---

## 9. MVP Acceptance Criteria

The component is MVP-complete when:

1. ✅ BenchPRO client can submit TaskRuns via `POST /api/v1/task_runs`
2. ✅ Results Explorer with filters, sorting, pagination
3. ✅ CSV export of filtered results
4. ✅ Line/scatter/bar charts with animated transitions
5. ✅ Task detail view with FoMs and provenance
6. ✅ Inline viewing of stdout and modules artifacts
7. ✅ Saved views CRUD with visibility control
8. ✅ PAT management in the portal
9. ✅ Single-command local dev setup
10. ✅ Basic automated test suite

---

## 10. Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-01 | 1.0 | Initial implementation plan |
| 2025-12-01 | 1.1 | Phase 1 complete: Backend foundation, PostgreSQL, Alembic migrations, health endpoint |
| 2025-12-01 | 1.2 | Phase 2 complete: Pydantic schemas, CRUD services, security module, auth dependencies |
| 2025-12-01 | 1.3 | Phases 3-6 complete: All backend API endpoints implemented and tested |
| 2025-12-01 | 1.4 | Phases 7-10 complete: SvelteKit frontend with Results Explorer, Task Detail, Settings |
| 2025-12-01 | 1.5 | Phase 11 complete: Tests, seed data, documentation - MVP COMPLETE |

