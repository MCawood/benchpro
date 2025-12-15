# BenchPro 2.0 Developer Notes

## Project Overview
BenchPro 2.0 is a deterministic benchmark orchestrator for HPC systems. It separates the "application build" from the "benchmark execution" into two distinct phases, allowing for reusable builds and reproducible benchmarks.

**Core Philosophy:**
- **Deterministic**: The same input configuration should always produce the same output (or fail explicitly).
- **Separation of Concerns**: Builds produce artifacts (binaries + module files); Benchmarks use those artifacts.
- **System Agnostic**: Abstracts the underlying scheduler (Slurm, Local) via a `SchedulerBackend` interface.

## Directory Structure
```
benchpro-ng/
├── src/benchpro/
│   ├── cli/            # CLI Command definitions (Click groups)
│   ├── core/           # Core business logic
│   │   ├── domain.py   # Pydantic data models (Task, Job, Build, Benchmark)
│   │   ├── scheduler.py # SchedulerBackend (Slurm, Local)
│   │   ├── executor.py # Execution logic (local async or Slurm submission)
│   │   ├── planner.py  # Converts high-level requests into Task objects
│   │   ├── results.py  # SQLite database interface (ResultStore)
│   │   ├── resolver.py # Logic for finding builds/apps
│   │   └── services/   # Complex service orchestration (JobBuilder)
│   └── templates/      # Jinja2 templates for scripts
├── tests/              # Pytest suite (unit, integration, e2e)
├── scripts/            # Helper scripts (install.sh, gen_module.sh)
├── docs/               # Documentation
└── examples/           # Example configs and benchmarks
```

## Key Components

### 1. Configuration (`core/config.py`)
Configuration is hierarchical:
1.  **Defaults**: Hardcoded in `Config` class.
2.  **Site Config**: `$BENCHPRO_SITE_CONFIG` or `/path/to/install/config`.
3.  **User Config**: `~/.config/benchpro/config.yaml`.
4.  **Runtime**: CLI flags override config.

### 2. Scheduler Backend (`core/scheduler.py`)
Abstract base class `SchedulerBackend`.
-   **SlurmBackend**: Uses `sbatch`, `scancel`, `sacct`. Handles job dependencies (`--dependency=afterok:ID`).
-   **LocalBackend**: Runs tasks as local subprocesses (synchronously for now, but async friendly).
-   **MockSchedulerBackend** (in tests): Mocks scheduler interactions.

### 3. Module Management
BenchPro integrates with environment modules (Lmod).
-   **Generation**: When building an app, BenchPro generates a Lua module file in `workspaces/apps/{id}/modulefiles`.
-   **Usage**: Benchmarks use `module use {workspace}/modulefiles` to activate the custom environment.
-   **Logic**: `cli/build.py` handles generation; `core/planner.py` handles usage injection.

### 4. Job Chaining
To support `bp app build && bp bench run` workflows:
1.  **Planner** checks if the required build is PENDING/RUNNING.
2.  If so, it attaches the build's Job ID to the `Task` (`scheduler_dependencies`).
3.  **JobBuilder** aggregates task dependencies into the `Job`.
4.  **Executor** submits the job to Slurm with `--dependency=afterok:{build_job_id}`.

### 5. Safe Deletion
Deleting an active run or build requires careful handling:
1.  **Identify Active Jobs**: Check status.
2.  **Cancel**: Call `scheduler.cancel_job()`.
3.  **Wait**: Poll `scheduler.wait_for_jobs()`.
4.  **Cleanup**: Delete filesystem and DB records only after jobs terminate.

## Testing
Run tests using `pytest` from the project root.
```bash
pytest
```
-   **Unit Tests**: `tests/unit/` - Fast, mock dependent components.
-   **Integration Tests**: `tests/integration/` - Test component interactions (requires specific environment/mocks).
-   **E2E Tests**: `tests/e2e/` - CLI invocation tests.

**Note**: Some tests mock Slurm behaviors. The `MockSchedulerBackend` in `tests/conftest.py` is crucial for this.

## Development Workflow
1.  **Virtual Environment**: Use the provided `venv` or create your own.
2.  **Install Editable**: `pip install -e .`
3.  **Run Locally**: `bp app list`, `bp bench run ...`

## Future Considerations
-   **MPI Integration**: Deepen MPI launcher support (srun vs mpirun).
-   **Container Support**: Abstracting environments further with Singularity/Apptainer.
-   **Result Analysis**: Enhanced metrics parsing and plotting.
