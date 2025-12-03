# BenchPRO Results Server - User Guide

**For BenchPRO Users**

This guide explains how to submit benchmark results and use the web portal to explore, analyze, and download your data.

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Submitting Results](#submitting-results)
4. [Using the Web Portal](#using-the-web-portal)
5. [Filtering and Sorting](#filtering-and-sorting)
6. [Viewing Task Details](#viewing-task-details)
7. [Examining Provenance](#examining-provenance)
8. [Downloading Data](#downloading-data)
9. [Saved Views](#saved-views)
10. [API Token Management](#api-token-management)

---

## Overview

The BenchPRO Results Server provides centralized storage and visualization for your HPC benchmark results. Key features:

- **Automatic submission** from BenchPRO client after benchmark completion
- **Web portal** for browsing, filtering, and comparing results
- **Provenance tracking** with metadata and artifacts (logs, scripts, configs)
- **Saved views** to bookmark your favorite filter combinations
- **Data export** for offline analysis

---

## Getting Started

### Accessing the Portal

Navigate to your institution's BenchPRO Results Server:

```
https://results.hpc.your-institution.edu
```

### Authentication

1. Click **Login** in the top-right corner
2. Authenticate with your institutional credentials (SSO/OIDC)
3. On first login, your account is automatically created

### Creating an API Token

To submit results from the BenchPRO client, you need a Personal Access Token (PAT):

1. Navigate to **Settings** (gear icon)
2. Click **Create New Token**
3. Enter a descriptive name (e.g., "Frontera submissions")
4. Click **Generate**
5. **Copy the token immediately** - it won't be shown again!

---

## Submitting Results

### Automatic Submission (BenchPRO Client)

> **Note:** This section will be updated when client-side integration is complete.

When running benchmarks with BenchPRO, results are automatically submitted to the server after completion:

```bash
# Configure your API token (one-time setup)
bp config set results.server_url https://results.hpc.example.edu
bp config set results.api_token bp_your_token_here

# Run a benchmark suite - results automatically upload
bp suite run lammps_suite.yaml
```

### Manual Submission (Advanced)

For custom integrations, you can submit results directly via the API:

```bash
curl -X POST "https://results.hpc.example.edu/api/v1/task_runs" \
  -H "Authorization: Bearer bp_your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "client": {
      "benchpro_version": "2.0.0",
      "task_uuid": "unique-uuid-for-this-run"
    },
    "task": {
      "label": "lammps_ljmelt_128n",
      "system": "frontera",
      "node_count": 128,
      "runtime_seconds": 3600,
      "status": "completed",
      "submit_time": "2025-01-15T10:00:00Z"
    },
    "figures_of_merit": [
      {
        "name": "performance",
        "value_numeric": 12345.67,
        "unit": "timesteps/sec",
        "is_primary": true
      }
    ]
  }'
```

See [Client Submission Specification](CLIENT_SUBMISSION_SPEC.md) for complete details.

---

## Using the Web Portal

### Results Explorer

The main dashboard shows all benchmark results in a sortable table:

| Column | Description |
|--------|-------------|
| **Label** | Benchmark run identifier |
| **System** | HPC system name (e.g., Frontera, Stampede3) |
| **Nodes** | Number of compute nodes used |
| **Status** | Completion status (completed, failed, partial) |
| **Runtime** | Total execution time |
| **Submit Time** | When the benchmark was submitted |
| **Primary FoM** | Main figure of merit value |

### Quick Actions

- **Click a row** → View detailed task information
- **Click column headers** → Sort by that column
- **Use filter panel** → Narrow results by criteria

---

## Filtering and Sorting

### Filter Panel

Located on the left side of the Results Explorer:

| Filter | Options | Example |
|--------|---------|---------|
| **System** | Multi-select checkboxes | Frontera, Stampede3 |
| **Status** | Dropdown | completed, failed, partial |
| **Node Count** | Min/Max range | 32 - 128 |
| **Date Range** | Calendar picker | Last 30 days |
| **Benchmark** | Search/select | lammps_ljmelt |
| **Search** | Free text | "my_experiment" |

### Applying Filters

1. Select your filter criteria in the left panel
2. Click **Apply Filters** or filters apply automatically
3. Results table updates to show matching runs
4. Active filters shown as "chips" above the table
5. Click **Clear All** to reset

### Sorting

- Click any column header to sort ascending
- Click again for descending
- Current sort indicated by arrow icon

---

## Viewing Task Details

Click any row in the Results Explorer to open the Task Detail view.

### Summary Section

Displays key information:

```
┌─────────────────────────────────────────────┐
│ lammps_ljmelt_128n                          │
│ System: Frontera | Nodes: 128 | Completed   │
│ Runtime: 3600s | Submitted: Jan 15, 2025    │
└─────────────────────────────────────────────┘
```

### Figures of Merit

All performance metrics captured:

| Name | Value | Unit | Primary |
|------|-------|------|---------|
| performance | 12,345.67 | timesteps/sec | ✓ |
| memory_peak | 64.2 | GB | |
| io_bandwidth | 1.5 | GB/s | |

### Application Info

Details about the software used:

- **Application**: LAMMPS v23Jun2022
- **Modules**: intel/23.1, impi/21.9
- **Build User**: jsmith
- **Build Time**: Jan 10, 2025

### Benchmark Definition

Information about the benchmark configuration:

- **Label**: lammps_ljmelt
- **Description**: Lennard-Jones melt benchmark
- **Primary FoM**: timesteps/sec

---

## Examining Provenance

The **Provenance** tab contains detailed metadata and artifacts for reproducibility.

### Metadata

Key-value pairs captured during the run:

| Key | Value |
|-----|-------|
| git_commit | abc123def456 |
| scheduler | {"type": "slurm", "job_id": "12345"} |
| modules | ["intel/23.1", "impi/21.9"] |
| environment | {"OMP_NUM_THREADS": "4"} |

### Artifacts

Files captured from the benchmark run:

| Name | Type | Size |
|------|------|------|
| stdout | text/plain | 15 KB |
| stderr | text/plain | 2 KB |
| input_script | text/plain | 1 KB |
| job_script | text/plain | 500 B |

### Viewing Artifact Content

1. Click the artifact name to expand
2. Text files display inline (up to 100 KB)
3. Larger files show a preview with "Download" option
4. Binary files only available for download

### Downloading Artifacts

- **Single artifact**: Click the download icon next to the artifact
- **All artifacts**: Click **Download All** to get a ZIP archive

---

## Downloading Data

### Export Options

From the Results Explorer:

1. Apply your desired filters
2. Click **Export** button in the toolbar
3. Choose format:
   - **CSV** - Spreadsheet-compatible
   - **JSON** - Complete data with nested structures
   - **Parquet** - Efficient columnar format for analysis

### What's Included

Export includes:

- Task run metadata (label, system, nodes, runtime, status)
- Figures of merit (all captured metrics)
- Application information
- Benchmark definition
- Submit/start/end times

Provenance artifacts are **not** included in bulk exports. Download those individually from the Task Detail view.

### API Export

For programmatic access:

```bash
# Export filtered results as JSON
curl "https://results.example.edu/api/v1/task_runs?system=frontera&per_page=1000" \
  -H "Authorization: Bearer bp_your_token"
```

---

## Saved Views

Save your frequently used filter combinations for quick access.

### Creating a Saved View

1. Set up your filters in the Results Explorer
2. Click **Save View** in the toolbar
3. Enter a name and optional description
4. Choose visibility:
   - **Private** - Only you can see it
   - **Public** - Visible to all users
5. Click **Save**

### Using Saved Views

1. Navigate to **Saved Views** in the sidebar
2. Click a view name to load it
3. Filters automatically apply to Results Explorer

### Managing Saved Views

From the Saved Views page:

- **Edit**: Change name, description, or visibility
- **Delete**: Remove views you no longer need
- **Duplicate**: Create a copy to modify

---

## API Token Management

### Viewing Your Tokens

1. Go to **Settings** → **API Tokens**
2. See all your active tokens with:
   - Name
   - Created date
   - Last used date

### Creating a Token

1. Click **Create New Token**
2. Enter a descriptive name
3. Click **Generate**
4. Copy the token immediately (shown only once!)

### Revoking a Token

1. Find the token in the list
2. Click the **Revoke** button
3. Confirm the action

**Warning**: Revoked tokens immediately stop working. Any scripts using that token will fail.

### Best Practices

- Use descriptive names (e.g., "Frontera-Laptop", "CI-Pipeline")
- Create separate tokens for different use cases
- Revoke tokens you no longer need
- Never share tokens or commit them to version control

---

## Tips and Tricks

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search box |
| `Esc` | Clear current filters |
| `Enter` | Apply filters |
| `←` `→` | Navigate pages |

### Comparing Runs

1. Select multiple runs using checkboxes
2. Click **Compare** in the toolbar
3. View side-by-side metrics and configurations

### Finding Your Runs

Use the search box with your username:
```
user:jsmith system:frontera
```

### Bookmarking Results

The URL updates as you apply filters. Bookmark or share the URL to return to the same view later.

---

## Getting Help

- **Documentation**: Links in the portal footer
- **Support**: Contact your HPC center's support team
- **Issues**: Report bugs to your site administrators

