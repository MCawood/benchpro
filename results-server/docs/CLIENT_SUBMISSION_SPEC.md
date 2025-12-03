# BenchPRO Results Server - Client Submission Specification

**For Client Developers**

This document specifies the data format and requirements for submitting benchmark results to the BenchPRO Results Server. It serves as the bridge between client-side BenchPRO implementations and the server API.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Submission Endpoint](#submission-endpoint)
4. [Request Schema](#request-schema)
5. [Field Reference](#field-reference)
6. [Figures of Merit](#figures-of-merit)
7. [Provenance Data](#provenance-data)
8. [Response Format](#response-format)
9. [Idempotency](#idempotency)
10. [Limitations](#limitations)
11. [Error Handling](#error-handling)
12. [Examples](#examples)

---

## Overview

The submission API allows BenchPRO clients to upload benchmark results, performance metrics, and provenance data to a central server for storage and analysis.

### Key Concepts

- **Task Run**: A single execution of a benchmark
- **Figure of Merit (FoM)**: A measured performance metric
- **Provenance**: Metadata and artifacts for reproducibility
- **Idempotency**: Safe to retry submissions without creating duplicates

### Base URL

```
https://results.hpc.example.edu/api/v1
```

---

## Authentication

All submissions require a Personal Access Token (PAT).

### Token Format

Tokens are prefixed with `bp_` followed by a random string:

```
bp_7f3a9c2e1d4b5f6a8e9c0d1b2f3a4e5c
```

### Header

Include the token in the `Authorization` header:

```http
Authorization: Bearer bp_your_token_here
```

### Obtaining a Token

Users create tokens via:
1. Web portal: Settings → API Tokens → Create New Token
2. (Future) CLI: `bp auth token create --name "My Token"`

### Token Security

- Tokens are hashed server-side (Argon2)
- Tokens cannot be retrieved after creation
- Revoked tokens immediately stop working
- Tokens are user-specific (submissions attributed to token owner)

---

## Submission Endpoint

```http
POST /api/v1/task_runs
Content-Type: application/json
Authorization: Bearer <token>
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `201 Created` | Submission successful (new or duplicate) |
| `400 Bad Request` | Invalid request body |
| `401 Unauthorized` | Missing or invalid token |
| `422 Unprocessable Entity` | Validation error |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error |

---

## Request Schema

### Top-Level Structure

```json
{
  "client": { ... },           // Required: Client metadata
  "task": { ... },             // Required: Task run details
  "application": { ... },      // Optional: Application info
  "benchmark_definition": { ... }, // Optional: Benchmark config
  "figures_of_merit": [ ... ], // Optional: Performance metrics
  "provenance": { ... }        // Optional: Reproducibility data
}
```

### Complete Schema (TypeScript)

```typescript
interface TaskRunSubmission {
  client: ClientInfo;
  task: TaskInfo;
  application?: ApplicationInfo;
  benchmark_definition?: BenchmarkDefinitionInfo;
  figures_of_merit?: FigureOfMerit[];
  provenance?: ProvenanceData;
}

interface ClientInfo {
  benchpro_version: string;  // Required: e.g., "2.0.0"
  task_uuid: string;         // Required: UUID v4
  client_hostname?: string;
  submit_timestamp?: string; // ISO 8601
}

interface TaskInfo {
  label: string;             // Required: Task identifier
  system: string;            // Required: HPC system name
  status: TaskStatus;        // Required: Completion status
  submit_time: string;       // Required: ISO 8601 timestamp
  architecture?: string;
  node_count?: number;
  runtime_seconds?: number;
  start_time?: string;       // ISO 8601
  end_time?: string;         // ISO 8601
  extra?: object;            // Additional metadata
}

type TaskStatus = "pending" | "running" | "completed" | "failed" | "partial" | "cancelled";

interface ApplicationInfo {
  label: string;             // Required: App name (e.g., "lammps")
  version?: string;          // e.g., "23Jun2022"
  system?: string;           // Build system
  architecture?: string;     // Build architecture
  modules?: string[];        // Module list
  build_user?: string;
  build_time?: string;       // ISO 8601
  extra?: object;
}

interface BenchmarkDefinitionInfo {
  label: string;             // Required: Benchmark identifier
  description?: string;
  default_primary_fom_name?: string;
}

interface FigureOfMerit {
  name: string;              // Required: Metric name
  value_numeric?: number;    // Numeric value (mutually exclusive with value_text)
  value_text?: string;       // Text value (mutually exclusive with value_numeric)
  unit?: string;             // Unit of measurement
  is_primary?: boolean;      // Default: false
  extra?: object;
}

interface ProvenanceData {
  metadata?: ProvenanceMetadata[];
  artifacts?: ProvenanceArtifact[];
}

interface ProvenanceMetadata {
  key: string;               // Required: Metadata key
  value_text?: string;       // Simple text value
  value_json?: object | any[]; // Complex JSON value
}

interface ProvenanceArtifact {
  name: string;              // Required: Artifact name
  content_type: string;      // Required: MIME type
  encoding?: "raw" | "gzip" | "base64";  // Default: "raw"
  data: string;              // Required: Base64-encoded content
}
```

---

## Field Reference

### client (Required)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `benchpro_version` | string | ✓ | BenchPRO client version (e.g., "2.0.0") |
| `task_uuid` | string (UUID) | ✓ | Unique identifier for this task run |
| `client_hostname` | string | | Hostname where client ran |
| `submit_timestamp` | string (ISO 8601) | | When client initiated submission |

**task_uuid Requirements:**
- Must be a valid UUID v4
- Must be unique per task run
- Used for idempotency (duplicate detection)
- Generate with: `uuid.uuid4()` (Python) or `crypto.randomUUID()` (JS)

### task (Required)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | ✓ | Human-readable task identifier |
| `system` | string | ✓ | HPC system name (e.g., "frontera") |
| `status` | enum | ✓ | Task completion status |
| `submit_time` | string (ISO 8601) | ✓ | Job submission timestamp |
| `architecture` | string | | CPU architecture (e.g., "intel_spr") |
| `node_count` | integer | | Number of compute nodes |
| `runtime_seconds` | float | | Total execution time in seconds |
| `start_time` | string (ISO 8601) | | Job start timestamp |
| `end_time` | string (ISO 8601) | | Job completion timestamp |
| `extra` | object | | Additional metadata as JSON |

**status Values:**

| Value | When to Use |
|-------|-------------|
| `pending` | Task queued but not started |
| `running` | Task currently executing |
| `completed` | Task finished successfully |
| `failed` | Task encountered fatal error |
| `partial` | Task completed with some results |
| `cancelled` | Task was manually cancelled |

### application (Optional)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | ✓ | Application name (e.g., "lammps", "hpl") |
| `version` | string | | Version string |
| `system` | string | | System where application was built |
| `architecture` | string | | Build architecture |
| `modules` | string[] | | List of modules loaded |
| `build_user` | string | | Username who built the application |
| `build_time` | string (ISO 8601) | | Build timestamp |
| `extra` | object | | Additional build metadata |

**Matching Logic:**
Applications are matched by `(label, version, system, architecture)`. If no match exists, a new application record is created.

### benchmark_definition (Optional)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | ✓ | Unique benchmark identifier |
| `description` | string | | Human-readable description |
| `default_primary_fom_name` | string | | Expected primary metric name |

**Matching Logic:**
Benchmark definitions are matched by `label`. If no match exists, a new definition is created.

---

## Figures of Merit

Figures of Merit (FoMs) are performance metrics captured during benchmark execution.

### Structure

```json
{
  "figures_of_merit": [
    {
      "name": "performance",
      "value_numeric": 12345.67,
      "unit": "GFLOPS",
      "is_primary": true
    },
    {
      "name": "memory_peak",
      "value_numeric": 64.2,
      "unit": "GB",
      "is_primary": false
    },
    {
      "name": "status_message",
      "value_text": "All tests passed",
      "is_primary": false
    }
  ]
}
```

### Field Details

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✓ | Metric identifier (lowercase, underscores) |
| `value_numeric` | float | † | Numeric measurement |
| `value_text` | string | † | Text value (for non-numeric metrics) |
| `unit` | string | | Unit of measurement |
| `is_primary` | boolean | | Mark as primary FoM (default: false) |
| `extra` | object | | Additional metadata |

† One of `value_numeric` or `value_text` is required.

### Naming Conventions

Recommended FoM names by benchmark type:

| Benchmark | FoM Name | Unit |
|-----------|----------|------|
| LAMMPS | `tau_day` | tau/day |
| HPL | `gflops` | GFLOPS |
| STREAM | `copy_bandwidth` | MB/s |
| IOR | `write_bandwidth` | GB/s |
| OSU | `latency_us` | μs |

### Primary FoM

- Only one FoM should have `is_primary: true`
- If multiple are marked primary, only the first is used
- Primary FoM is displayed prominently in the UI

---

## Provenance Data

Provenance captures metadata and artifacts for reproducibility.

### Metadata

Key-value pairs with text or JSON values:

```json
{
  "provenance": {
    "metadata": [
      {
        "key": "git_commit",
        "value_text": "abc123def456"
      },
      {
        "key": "environment",
        "value_json": {
          "OMP_NUM_THREADS": "4",
          "MPI_RANKS_PER_NODE": "8"
        }
      },
      {
        "key": "modules",
        "value_json": ["intel/23.1", "impi/21.9", "phdf5/1.14"]
      },
      {
        "key": "scheduler",
        "value_json": {
          "type": "slurm",
          "job_id": "12345678",
          "queue": "normal",
          "walltime_requested": "02:00:00"
        }
      }
    ]
  }
}
```

### Standard Metadata Keys

| Key | Type | Description |
|-----|------|-------------|
| `git_commit` | text | Git commit hash |
| `git_branch` | text | Git branch name |
| `git_repo` | text | Git repository URL |
| `modules` | json (array) | Module list |
| `environment` | json (object) | Environment variables |
| `scheduler` | json (object) | Scheduler info (type, job_id, queue) |
| `command_line` | text | Execution command |
| `working_directory` | text | Execution directory |
| `hostname` | text | Compute node hostname |

### Artifacts

Binary or text files captured from the run:

```json
{
  "provenance": {
    "artifacts": [
      {
        "name": "stdout",
        "content_type": "text/plain",
        "encoding": "gzip",
        "data": "H4sIAAAAAAAAA..."  // Base64-encoded gzip
      },
      {
        "name": "input_script",
        "content_type": "text/plain",
        "encoding": "raw",
        "data": "IyBMQU1NUFMgaW5wdXQgc2NyaXB0..."  // Base64
      }
    ]
  }
}
```

### Artifact Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✓ | Artifact identifier |
| `content_type` | string | ✓ | MIME type |
| `encoding` | enum | | `raw`, `gzip`, or `base64` (default: `raw`) |
| `data` | string | ✓ | Base64-encoded content |

### Common Artifacts

| Name | Content Type | Description |
|------|--------------|-------------|
| `stdout` | text/plain | Standard output |
| `stderr` | text/plain | Standard error |
| `input_script` | text/plain | Input configuration |
| `job_script` | text/plain | Batch job script |
| `output_log` | text/plain | Application log |
| `timing_data` | application/json | Detailed timing breakdown |

---

## Response Format

### Success Response (201 Created)

```json
{
  "status": "ok",
  "task_run_id": 123,
  "duplicate": false,
  "message": null
}
```

### Duplicate Response (201 Created)

```json
{
  "status": "ok",
  "task_run_id": 123,
  "duplicate": true,
  "message": "Task run already exists"
}
```

### Error Response (4xx/5xx)

```json
{
  "detail": "Error message here"
}
```

Or for validation errors (422):

```json
{
  "detail": [
    {
      "loc": ["body", "task", "system"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Idempotency

Submissions are idempotent based on `task_uuid`:

1. First submission with a UUID creates a new task run
2. Subsequent submissions with the same UUID return the existing task run
3. The `duplicate` field indicates whether it was a new or existing submission

### Client Implementation

```python
import uuid
import httpx

def submit_result(result_data: dict, api_token: str, server_url: str):
    # Generate or retrieve task UUID
    task_uuid = result_data.get('task_uuid') or str(uuid.uuid4())
    
    submission = {
        "client": {
            "benchpro_version": "2.0.0",
            "task_uuid": task_uuid,
        },
        "task": result_data['task'],
        # ... other fields
    }
    
    response = httpx.post(
        f"{server_url}/api/v1/task_runs",
        json=submission,
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=30.0,
    )
    
    if response.status_code == 201:
        data = response.json()
        if data['duplicate']:
            print(f"Task already submitted (ID: {data['task_run_id']})")
        else:
            print(f"Task submitted successfully (ID: {data['task_run_id']})")
        return data['task_run_id']
    else:
        response.raise_for_status()
```

### Retry Safety

Safe to retry on network errors:

```python
import time
from httpx import TimeoutException, NetworkError

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

for attempt in range(MAX_RETRIES):
    try:
        task_id = submit_result(result_data, token, server_url)
        break
    except (TimeoutException, NetworkError) as e:
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))
        else:
            raise
```

---

## Limitations

### Size Limits

| Component | Limit | Notes |
|-----------|-------|-------|
| Request body | 10 MB | Total JSON payload |
| Single artifact | 5 MB | Per-artifact data size |
| Total artifacts | 20 MB | Sum of all artifacts per submission |
| Metadata value_text | 64 KB | Per metadata entry |
| Metadata value_json | 1 MB | Per metadata entry |
| FoM count | 100 | Per task run |
| Metadata count | 100 | Per task run |
| Artifact count | 20 | Per task run |

### Rate Limits

| Scope | Limit | Window |
|-------|-------|--------|
| Submissions | 60 | per minute |
| API calls | 300 | per minute |

Rate limit headers in response:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200
```

### Data Retention

- Task runs: Indefinite (subject to site policy)
- Artifacts: 1 year default (configurable per site)
- Metadata: Indefinite

---

## Error Handling

### Common Errors

**400 Bad Request**
```json
{"detail": "Invalid JSON body"}
```
- Malformed JSON
- Missing required fields

**401 Unauthorized**
```json
{"detail": "Invalid or missing authentication token"}
```
- Token not provided
- Token revoked
- Token malformed

**422 Unprocessable Entity**
```json
{
  "detail": [
    {
      "loc": ["body", "figures_of_merit", 0],
      "msg": "Either value_numeric or value_text must be provided",
      "type": "value_error"
    }
  ]
}
```
- Validation failures
- Invalid enum values
- Missing mutually required fields

**429 Too Many Requests**
```json
{"detail": "Rate limit exceeded. Retry after 60 seconds."}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error"}
```
- Database errors
- Unexpected exceptions

### Error Recovery

```python
def handle_submission_error(response):
    if response.status_code == 400:
        # Fix request and retry
        raise ValueError(f"Invalid request: {response.json()}")
    
    elif response.status_code == 401:
        # Token issue - cannot retry with same token
        raise AuthenticationError("Check API token")
    
    elif response.status_code == 422:
        # Validation error - fix data
        errors = response.json().get('detail', [])
        raise ValidationError(errors)
    
    elif response.status_code == 429:
        # Rate limited - wait and retry
        retry_after = int(response.headers.get('Retry-After', 60))
        time.sleep(retry_after)
        return True  # Signal to retry
    
    elif response.status_code >= 500:
        # Server error - retry with backoff
        return True  # Signal to retry
    
    return False
```

---

## Examples

### Minimal Submission

```json
{
  "client": {
    "benchpro_version": "2.0.0",
    "task_uuid": "550e8400-e29b-41d4-a716-446655440000"
  },
  "task": {
    "label": "test_run",
    "system": "frontera",
    "status": "completed",
    "submit_time": "2025-01-15T10:00:00Z"
  }
}
```

### Complete Submission

```json
{
  "client": {
    "benchpro_version": "2.0.0",
    "task_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "client_hostname": "login1.frontera.tacc.utexas.edu",
    "submit_timestamp": "2025-01-15T14:30:00Z"
  },
  "task": {
    "label": "lammps_ljmelt_128n",
    "system": "frontera",
    "architecture": "intel_clx",
    "node_count": 128,
    "runtime_seconds": 3600.5,
    "status": "completed",
    "submit_time": "2025-01-15T10:00:00Z",
    "start_time": "2025-01-15T10:05:00Z",
    "end_time": "2025-01-15T11:05:30Z"
  },
  "application": {
    "label": "lammps",
    "version": "23Jun2022",
    "system": "frontera",
    "architecture": "intel_clx",
    "modules": ["intel/19.1", "impi/19.0", "lammps/23Jun2022"]
  },
  "benchmark_definition": {
    "label": "lammps_ljmelt",
    "description": "LAMMPS Lennard-Jones melt benchmark",
    "default_primary_fom_name": "tau_day"
  },
  "figures_of_merit": [
    {
      "name": "tau_day",
      "value_numeric": 1234567.89,
      "unit": "tau/day",
      "is_primary": true
    },
    {
      "name": "atoms_per_second",
      "value_numeric": 5678901.23,
      "unit": "atoms/s",
      "is_primary": false
    },
    {
      "name": "memory_peak_gb",
      "value_numeric": 245.7,
      "unit": "GB",
      "is_primary": false
    }
  ],
  "provenance": {
    "metadata": [
      {"key": "git_commit", "value_text": "abc123def456789"},
      {"key": "modules", "value_json": ["intel/19.1", "impi/19.0", "lammps/23Jun2022"]},
      {"key": "environment", "value_json": {
        "OMP_NUM_THREADS": "1",
        "I_MPI_PIN_DOMAIN": "core"
      }},
      {"key": "scheduler", "value_json": {
        "type": "slurm",
        "job_id": "12345678",
        "queue": "normal",
        "nodes_requested": 128,
        "walltime_requested": "02:00:00"
      }}
    ],
    "artifacts": [
      {
        "name": "stdout",
        "content_type": "text/plain",
        "encoding": "gzip",
        "data": "H4sIAAAAAAAAA0tJTc5IzcnJVyjPL8pJAQBSCkbLCwAAAA=="
      },
      {
        "name": "in.melt",
        "content_type": "text/plain",
        "encoding": "raw",
        "data": "IyBMQU1NUFMgaW5wdXQgZmlsZQp1bml0cyBsag=="
      }
    ]
  }
}
```

### Python Client Example

```python
#!/usr/bin/env python3
"""Example BenchPRO client submission."""

import gzip
import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

def encode_artifact(file_path: Path, compress: bool = True) -> dict:
    """Encode a file as a provenance artifact."""
    content = file_path.read_bytes()
    
    if compress and len(content) > 1024:
        compressed = gzip.compress(content)
        return {
            "name": file_path.name,
            "content_type": "text/plain",
            "encoding": "gzip",
            "data": base64.b64encode(compressed).decode('ascii'),
        }
    else:
        return {
            "name": file_path.name,
            "content_type": "text/plain",
            "encoding": "raw",
            "data": base64.b64encode(content).decode('ascii'),
        }


def submit_benchmark_result(
    server_url: str,
    api_token: str,
    label: str,
    system: str,
    node_count: int,
    runtime_seconds: float,
    figures_of_merit: list[dict],
    stdout_file: Path = None,
):
    """Submit a benchmark result to the server."""
    
    submission = {
        "client": {
            "benchpro_version": "2.0.0",
            "task_uuid": str(uuid.uuid4()),
        },
        "task": {
            "label": label,
            "system": system,
            "node_count": node_count,
            "runtime_seconds": runtime_seconds,
            "status": "completed",
            "submit_time": datetime.now(timezone.utc).isoformat(),
        },
        "figures_of_merit": figures_of_merit,
    }
    
    # Add stdout if provided
    if stdout_file and stdout_file.exists():
        submission["provenance"] = {
            "artifacts": [encode_artifact(stdout_file)],
        }
    
    response = httpx.post(
        f"{server_url}/api/v1/task_runs",
        json=submission,
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=30.0,
    )
    response.raise_for_status()
    
    result = response.json()
    print(f"Submitted: task_run_id={result['task_run_id']}, duplicate={result['duplicate']}")
    return result


# Usage
if __name__ == "__main__":
    submit_benchmark_result(
        server_url="http://localhost:8000",
        api_token="bp_your_token_here",
        label="my_benchmark_run",
        system="frontera",
        node_count=64,
        runtime_seconds=1800.5,
        figures_of_merit=[
            {"name": "performance", "value_numeric": 1234.56, "unit": "GFLOPS", "is_primary": True},
        ],
        stdout_file=Path("benchmark.out"),
    )
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01 | Initial specification |

