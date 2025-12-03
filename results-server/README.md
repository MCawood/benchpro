# BenchPRO Results Server

The Results Collection & Visualization component for BenchPRO 2.0. This system provides centralized storage and visualization of HPC benchmark results.

## Features

- **REST API** for submitting and querying benchmark results
- **Web Portal** for exploring results, visualizing FoMs, and managing saved views
- **PostgreSQL** storage for benchmark data and provenance artifacts
- **Idempotent submission** with automatic deduplication
- **Personal Access Tokens** for secure client authentication

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

### 1. Start PostgreSQL

```bash
cd results-server
docker-compose up -d postgres
```

### 2. Set up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# (Optional) Load seed data for testing
python ../seed/seed_data.py

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000/api/v1
- **Swagger Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/v1/health

### 3. Set up Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The web portal will be available at:
- **Frontend**: http://localhost:5173

## Project Structure

```
results-server/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/          # API route handlers
│   │   ├── core/            # Configuration, security
│   │   ├── db/              # Database models, session
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Database migrations
│   ├── tests/               # Unit and integration tests
│   └── requirements.txt
│
├── frontend/                # SvelteKit web portal
│   ├── src/
│   │   ├── lib/             # API client, stores, components
│   │   └── routes/          # Page components
│   └── package.json
│
├── seed/                    # Seed data scripts
├── docker-compose.yaml
├── IMPLEMENTATION_PLAN.md
└── README.md
```

## API Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check (unauthenticated) |

### Task Runs
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/task_runs` | Submit a task run |
| GET | `/api/v1/task_runs` | List/filter task runs |
| GET | `/api/v1/task_runs/{id}` | Get task run details |
| GET | `/api/v1/task_runs/{id}/provenance` | Get provenance data |

### Provenance
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/provenance_artifacts/{id}` | Get artifact content |

### Metadata
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/applications` | List applications |
| GET | `/api/v1/benchmark_definitions` | List benchmarks |

### Saved Views
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/saved_views` | List saved views |
| POST | `/api/v1/saved_views` | Create saved view |
| GET | `/api/v1/saved_views/{id}` | Get saved view |
| PUT | `/api/v1/saved_views/{id}` | Update saved view |
| DELETE | `/api/v1/saved_views/{id}` | Delete saved view |

### API Tokens
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/api_tokens` | List user's tokens |
| POST | `/api/v1/api_tokens` | Create new token |
| DELETE | `/api/v1/api_tokens/{id}` | Revoke token |

## Configuration

Copy `env.example` to `.env` in the backend directory and adjust as needed:

```bash
cp env.example backend/.env
```

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `SECRET_KEY` | JWT signing key | (change in production!) |
| `DEBUG` | Enable debug mode and API docs | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Development

### Database Migrations

```bash
cd backend
source venv/bin/activate

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1
```

### Running Tests

```bash
cd backend
source venv/bin/activate

# Create test database first
docker exec benchpro-results-db psql -U benchpro -c "CREATE DATABASE benchpro_results_test"

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/integration/test_task_runs.py -v
```

### Seed Data

Generate sample data for development/testing:

```bash
cd backend
source venv/bin/activate
python ../seed/seed_data.py
```

This creates:
- 3 users (1 admin, 2 regular)
- Multiple applications across systems
- 5 benchmark definitions
- 50 task runs with FoMs and provenance
- 3 saved views

## Submitting Results from BenchPRO Client

### Example Submission

```python
import httpx
from uuid import uuid4
from datetime import datetime

# Create a PAT in the web portal first
TOKEN = "bp_your_token_here"

submission = {
    "client": {
        "benchpro_version": "2.0.0",
        "task_uuid": str(uuid4()),
    },
    "task": {
        "label": "lammps_ljmelt_4n",
        "system": "stampede3",
        "architecture": "intel_spr",
        "node_count": 4,
        "runtime_seconds": 120.5,
        "status": "completed",
        "submit_time": datetime.now().isoformat(),
    },
    "application": {
        "label": "lammps",
        "version": "23Jun2022",
        "system": "stampede3",
    },
    "benchmark_definition": {
        "label": "lammps_ljmelt",
        "default_primary_fom_name": "tau_day",
    },
    "figures_of_merit": [
        {
            "name": "tau_day",
            "value_numeric": 1234.56,
            "unit": "tau/day",
            "is_primary": True,
        },
    ],
}

response = httpx.post(
    "http://localhost:8000/api/v1/task_runs",
    json=submission,
    headers={"Authorization": f"Bearer {TOKEN}"},
)
print(response.json())
```

## Architecture

### Backend Stack
- **FastAPI** - Async Python web framework
- **SQLAlchemy 2.0** - Async ORM
- **PostgreSQL** - Database
- **Alembic** - Migrations
- **Pydantic v2** - Validation
- **Argon2** - Password hashing

### Frontend Stack
- **SvelteKit** - Web framework
- **TailwindCSS** - Styling
- **ECharts** - Data visualization

## Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Audience | Description |
|----------|----------|-------------|
| [Setup Guide](docs/SETUP_GUIDE.md) | Site Maintainers | Deployment, configuration, administration |
| [User Guide](docs/USER_GUIDE.md) | BenchPRO Users | Using the portal, submitting results |
| [Schema Reference](docs/SCHEMA_REFERENCE.md) | Developers | Database schema, models, patterns |
| [Client Submission Spec](docs/CLIENT_SUBMISSION_SPEC.md) | Client Developers | API format, limits, examples |

Additional resources:
- **Swagger UI**: http://localhost:8000/api/docs (when running)
- **Implementation Plan**: See `IMPLEMENTATION_PLAN.md` for development roadmap

## License

MIT License - See LICENSE file for details.
