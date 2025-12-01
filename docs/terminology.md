# BenchPRO 2.0 Terminology

To ensure clarity and consistency throughout the project, the following terminology is used:

## Core Concepts

### Task
A **Task** is the fundamental unit of operation in BenchPRO. It represents a specific action to be performed.
- **Types**:
    - **Build Task**: Compiles and installs an application.
    - **Benchmark Task**: Runs a performance benchmark, typically using a pre-built application.
- **Definition**: Tasks are defined in **Task Profiles** (YAML files).

### Profile
A **Profile** is a blueprint for a Task. It contains all the necessary parameters, template variables, and resource requirements to execute a Task.
- **Location**: User profiles are stored in `~/.config/benchpro/profiles`. Site profiles are in `$BENCHPRO_SITE_PROFILES`.

### Application (App)
An **Application** is the concrete artifact resulting from a successful **Build Task**.
- **Nature**: It is a compiled software package (binaries, libraries, modules).
- **Usage**: Built once, used by multiple Benchmark Tasks.
- **Storage**: Installed into the `apps/` directory (e.g., `$SCRATCH/benchpro/apps`).

### Benchmark
A **Benchmark** is the execution of a **Benchmark Task**.
- **Nature**: It runs a workload to measure performance.
- **Dependency**: Often depends on a specific **Application** (e.g., a LAMMPS benchmark depends on a LAMMPS app).

### Workspace
A **Workspace** is the isolated filesystem directory where a Task executes.
- **Purpose**: Provides a sandbox for the Task execution. Contains generated scripts, input files, and raw output logs.
- **Lifecycle**: Created before execution. Can be ephemeral (deleted after success) or persistent (for debugging).
- **Storage**: Located in the `workspaces/` directory (e.g., `$SCRATCH/benchpro/workspaces`).

### Result
A **Result** is the structured data captured from a Task execution.
- **Content**: Performance metrics (FLOPS, wall time), metadata (hardware info, timestamp), and status (PASS/FAIL).
- **Storage**: Parsed from the Workspace and stored in the **Result Store** (database/JSON) in the `results/` directory.

## Directory Structure Mapping

| Term | Directory | Description |
|------|-----------|-------------|
| **Application** | `apps/` | Installed binaries and module files. |
| **Workspace** | `workspaces/` | Execution sandbox (inputs, scripts, raw logs). |
| **Result** | `results/` | Structured performance data and metadata. |
