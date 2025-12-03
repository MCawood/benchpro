# BenchPRO Results Server - Setup Guide

**For Site Maintainers**

This guide covers deployment and administration of the BenchPRO Results Server for HPC centers and institutions.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Development)](#quick-start-development)
3. [Production Deployment](#production-deployment)
4. [Configuration Reference](#configuration-reference)
5. [Database Administration](#database-administration)
6. [Backup and Recovery](#backup-and-recovery)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB | 100+ GB (scales with artifact storage) |

### Software Requirements

- **Docker** 20.10+ and **Docker Compose** v2+
- **Python** 3.11+ (for running backend directly)
- **Node.js** 20+ (for frontend development)
- **PostgreSQL** 15+ (provided via Docker or external)

---

## Quick Start (Development)

For local development and testing:

```bash
# Clone the repository
cd benchpro_antigravity/results-server

# Start PostgreSQL
docker-compose up -d postgres

# Set up backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# (Optional) Load sample data
python ../seed/seed_data.py

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000/api/v1
- **Swagger Docs**: http://localhost:8000/api/docs

### Frontend (Optional)

```bash
cd frontend
npm install
npm run dev
```

Frontend available at http://localhost:5173

---

## Production Deployment

### Option 1: Docker Compose (Recommended)

Create a `docker-compose.prod.yaml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: benchpro-results-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: benchpro_results
      POSTGRES_USER: benchpro
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U benchpro -d benchpro_results"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://benchpro:${DB_PASSWORD}@postgres:5432/benchpro_results
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "false"
      LOG_LEVEL: INFO
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "3000:3000"

volumes:
  postgres_data:
```

Create a `.env` file:

```bash
DB_PASSWORD=your-secure-database-password
SECRET_KEY=your-256-bit-secret-key-for-jwt-signing
```

Deploy:

```bash
docker-compose -f docker-compose.prod.yaml up -d
```

### Option 2: Kubernetes

See `deploy/kubernetes/` for Helm charts and manifests (coming soon).

### Option 3: Systemd Services

For bare-metal deployment:

```ini
# /etc/systemd/system/benchpro-results.service
[Unit]
Description=BenchPRO Results Server
After=network.target postgresql.service

[Service]
Type=simple
User=benchpro
WorkingDirectory=/opt/benchpro-results/backend
Environment="DATABASE_URL=postgresql+asyncpg://..."
Environment="SECRET_KEY=..."
ExecStart=/opt/benchpro-results/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` | Yes |
| `SECRET_KEY` | JWT signing key (min 32 chars) | - | **Yes (production)** |
| `DEBUG` | Enable debug mode | `true` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | `60` | No |
| `RATE_LIMIT_SUBMISSIONS_PER_MINUTE` | Submission rate limit | `60` | No |

### OIDC/SSO Configuration (Optional)

| Variable | Description |
|----------|-------------|
| `OIDC_ISSUER` | OIDC provider URL (e.g., `https://auth.example.com`) |
| `OIDC_CLIENT_ID` | OAuth2 client ID |
| `OIDC_CLIENT_SECRET` | OAuth2 client secret |

### Example Production `.env`

```bash
# Database
DATABASE_URL=postgresql+asyncpg://benchpro:secure_password@db.example.com:5432/benchpro_results

# Security
SECRET_KEY=your-very-long-random-string-at-least-32-characters
DEBUG=false
LOG_LEVEL=INFO

# Optional: SSO
OIDC_ISSUER=https://auth.tacc.utexas.edu
OIDC_CLIENT_ID=benchpro-results
OIDC_CLIENT_SECRET=client-secret-here
```

---

## Database Administration

### Initial Setup

```bash
# Create database (if not using Docker)
createdb -U postgres benchpro_results

# Run migrations
cd backend
source venv/bin/activate
alembic upgrade head
```

### Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# View migration history
alembic history

# Create new migration (after model changes)
alembic revision --autogenerate -m "description"
```

### Database Maintenance

```sql
-- Check table sizes
SELECT 
    relname as table,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Vacuum and analyze
VACUUM ANALYZE;

-- Reindex if needed
REINDEX DATABASE benchpro_results;
```

---

## Backup and Recovery

### Automated Backups

```bash
#!/bin/bash
# /opt/benchpro/scripts/backup.sh

BACKUP_DIR=/var/backups/benchpro
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/benchpro_results_${TIMESTAMP}.sql.gz"

# Create backup
docker exec benchpro-results-db pg_dump -U benchpro benchpro_results | gzip > "$BACKUP_FILE"

# Retain last 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```
0 2 * * * /opt/benchpro/scripts/backup.sh
```

### Restore from Backup

```bash
# Stop the backend first
docker-compose stop backend

# Restore
gunzip -c backup_file.sql.gz | docker exec -i benchpro-results-db psql -U benchpro benchpro_results

# Restart
docker-compose start backend
```

---

## Monitoring and Maintenance

### Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health

# Database connectivity
docker exec benchpro-results-db pg_isready -U benchpro -d benchpro_results
```

### Log Management

```bash
# View backend logs
docker logs -f benchpro-results-backend

# Log rotation (logrotate.d config)
/var/log/benchpro/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

### Performance Monitoring

Key metrics to monitor:
- API response times (P50, P95, P99)
- Database connection pool utilization
- Disk usage (especially for provenance artifacts)
- Memory usage

Recommended tools:
- **Prometheus** + **Grafana** for metrics
- **pgBadger** for PostgreSQL log analysis

---

## Security Considerations

### Network Security

1. **Firewall Rules**
   - Only expose port 8000 (API) and 3000 (frontend) to users
   - PostgreSQL (5432) should only be accessible internally

2. **TLS/HTTPS**
   - Use a reverse proxy (nginx, Traefik) with TLS termination
   - Example nginx config:

```nginx
server {
    listen 443 ssl http2;
    server_name results.hpc.example.com;

    ssl_certificate /etc/ssl/certs/benchpro.crt;
    ssl_certificate_key /etc/ssl/private/benchpro.key;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

### Authentication

- **Development**: Auto-creates a dev user for testing
- **Production**: Configure OIDC/SSO or implement PAT-only auth
- **API Tokens**: Users generate Personal Access Tokens for CLI submissions

### Data Protection

- Database passwords stored in environment variables, not config files
- JWT secret key should be unique per deployment
- Consider encrypting provenance artifacts at rest

---

## Troubleshooting

### Common Issues

**Database Connection Refused**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check connection
docker exec benchpro-results-db pg_isready -U benchpro
```

**Migration Failures**
```bash
# Check current revision
alembic current

# Force to specific revision (use with caution)
alembic stamp head
```

**Out of Disk Space**
```sql
-- Find large artifacts
SELECT task_run_id, name, size_bytes 
FROM provenance_artifacts 
ORDER BY size_bytes DESC 
LIMIT 20;

-- Consider archiving old artifacts
```

**Slow Queries**
```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

-- Check for missing indexes
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public';
```

### Getting Help

- Check logs: `docker logs benchpro-results-backend`
- API errors include detailed messages in response body
- Open issues at: https://github.com/your-org/benchpro/issues

---

## Appendix: Quick Reference

### Useful Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart backend
docker-compose restart backend

# Database shell
docker exec -it benchpro-results-db psql -U benchpro -d benchpro_results

# Run migrations
cd backend && alembic upgrade head

# Generate new migration
cd backend && alembic revision --autogenerate -m "description"
```

### Default Ports

| Service | Port |
|---------|------|
| PostgreSQL | 5432 |
| Backend API | 8000 |
| Frontend | 5173 (dev) / 3000 (prod) |

