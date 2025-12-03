# BenchPRO Results Server Documentation

Welcome to the BenchPRO Results Server documentation. This directory contains comprehensive guides for different audiences.

---

## Documentation Index

### For Site Maintainers

**[Setup Guide](SETUP_GUIDE.md)**

Complete deployment and administration guide covering:
- Prerequisites and hardware requirements
- Development and production deployment options
- Configuration reference
- Database administration
- Backup and recovery
- Monitoring and maintenance
- Security considerations
- Troubleshooting

---

### For BenchPRO Users

**[User Guide](USER_GUIDE.md)**

How to use the Results Server to manage benchmark data:
- Submitting results from BenchPRO client
- Using the web portal
- Filtering and sorting results
- Viewing task details and provenance
- Downloading data and artifacts
- Managing saved views
- API token management

---

### For Developers

**[Schema Reference](SCHEMA_REFERENCE.md)**

Complete database schema documentation:
- Entity relationship diagram
- Table definitions and column types
- Enum types
- Index definitions
- SQLAlchemy model reference
- Pydantic schema patterns
- Migration examples

---

### For Client Developers

**[Client Submission Specification](CLIENT_SUBMISSION_SPEC.md)**

API specification for submitting results:
- Authentication (Personal Access Tokens)
- Request schema (JSON format)
- Field reference (all fields explained)
- Figures of Merit format
- Provenance data (metadata and artifacts)
- Response format
- Idempotency guarantees
- Size and rate limits
- Error handling
- Complete code examples

---

## Quick Links

| Resource | URL |
|----------|-----|
| API Documentation (Swagger) | `/api/docs` |
| API Documentation (ReDoc) | `/api/redoc` |
| OpenAPI Schema | `/api/openapi.json` |
| Health Check | `/api/v1/health` |

---

## Contributing to Documentation

Documentation is written in Markdown and lives in the `docs/` directory. To contribute:

1. Edit the relevant `.md` file
2. Follow existing formatting conventions
3. Test any code examples
4. Submit a pull request

### Style Guidelines

- Use ATX-style headers (`#`, `##`, `###`)
- Use fenced code blocks with language hints
- Include table of contents for long documents
- Provide practical examples
- Keep lines under 100 characters where possible

