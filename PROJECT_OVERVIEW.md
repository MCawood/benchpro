#1. Introduction
BenchPRO 2.0 is a Python-based orchestration tool for High-Performance Computing (HPC) benchmarking. Its primary goal is to automate building applications, running benchmarks, and collecting results on HPC systems (e.g., those using Slurm). This version is a complete rewrite of the original 1.0 codebase, leveraging modern libraries and design patterns for better maintainability, testability, and extensibility.

Key Improvements Over 1.0:
- Adoption of Domain-Driven Design (DDD).
- Use of YAML for configuration and Jinja2 for template rendering.
- Clear separation of concerns between domain models, services, and ports/adapters.
- Click for CLI commands and pytest for testing.



#2. High-Level Architecture
##2.1 Domain-Driven Design Layers
###2.1.1 Domain Layer (benchpro/core/domain/)
- Task: Represents a unit of work (build step, benchmark run, etc.) with state transitions (e.g., CREATED, RUNNING, COMPLETED, FAILED).
- Job: Contains one or more Tasks. A Job is often a multi-step HPC workflow and may hold timing info or logs.
- JobResources: HPC-specific resource definitions such as nodes, memory, cores, and walltime.

###2.1.2 Services Layer (benchpro/core/services/)
- BuildOrchestrator: Coordinates building applications by creating Tasks, rendering templates, and calling executors (local or HPC).
- TemplateService: Handles loading, rendering, and validating Jinja2-based templates (for both builds and runs).
- DatabaseService: Provides persistence logic (currently using SQLite, but may be refactored to a ports/adapters model).
- BuildLogger: Specialized logging for build processes (e.g., capturing output and logs).

###2.1.3 Ports & Adapters (benchpro/core/ports/ and benchpro/infrastructure/)
- Executor Interface (executor.py): Defines how jobs or tasks are executed (submit job, cancel job, check status).
- LocalExecutor: Implements Executor for local (non-HPC) testing or single-node runs.
- (Future) SlurmExecutor: Will implement Executor for actual HPC Slurm clusters.

##2.2 Other Project Components
- CLI (benchpro/cli/): Contains Click commands (benchpro, bp) for user-facing interactions (build, run, status, etc.).
- Templates (templates/):
    - YAML config (e.g., build.yaml) for HPC resource definitions, environment modules, or application-specific settings.
    - Jinja2 scripts (e.g., build.j2) that generate HPC submission scripts.
- Tests (various tests/ folders, depending on your structure):
    - pytest for unit, integration, and (eventually) HPC acceptance tests.
- Configuration (e.g., settings.py):
    - May use environment variables or a config.yaml file to store default behaviors, paths, or HPC site details.



#3. Core Use Cases & Workflows
##3.1 Build an HPC Application
- User runs benchpro build <app_name>.
- BuildOrchestrator reads the relevant YAML config + Jinja template (e.g., build.yaml, build.j2).
- A Job and associated Tasks are created to perform the build steps.
- An Executor (currently LocalExecutor, eventually SlurmExecutor) handles job submission or local execution.
- Output logs and metadata are captured via BuildLogger and stored in the database.

##3.2 Run a Benchmark
- Similar to building: define a YAML config with HPC parameters, a Jinja template for the run script.
- The user triggers a CLI command (benchpro run <benchmark_name>).
- A Job is created, Tasks are assigned resource requirements (JobResources), and the Executor executes them on HPC or locally.
- Results are collected, validated, and (future) uploaded or captured in the database.

##3.3 View Job/Task Status
- The user runs benchpro status <job_id> or something similar.
- The system retrieves info from the database (or HPC cluster via Executor) to display job state (QUEUED, RUNNING, COMPLETED, FAILED).



#4. HPC Integration
- Domain Models already incorporate HPC concepts (e.g., nodes, walltime).
- Executors:
    - LocalExecutor: for testing on a local machine or small single-node jobs.
    - (Planned) SlurmExecutor: Will handle sbatch submissions, job cancellation (scancel), and status checks (squeue or sacct).
- Resource Validation: Pydantic-based checks for fields, with potential for more advanced HPC partition/range validation in future releases.



#5. Project Goals & Roadmap
##5.1 Short Term (Stabilization):
- Fix failing tests and ensure basic features (builds, local runs) are stable.
- Add or improve unit/integration tests with pytest and address any architectural gaps.

##5.2 Mid Term (HPC Executor & Validation):
- Implement SlurmExecutor for real HPC job submission.
- Expand HPC resource validation (checking max nodes, memory constraints, partitions, etc.).

##5.3 Long Term (Dependencies, DB Refactor, HPC Modules):
- Add task dependency features (e.g., a multi-step pipeline: build → run → post-process).
- Migrate DatabaseService to a ports/adapters pattern if multiple backends or advanced queries are required.
- Integrate HPC environment modules or Lmod logic if needed.



#6. Key Directories & Files
Below is a quick reference to important paths:

- benchpro/core/domain/
    - task.py, job.py, job_resources.py – Domain models.
- benchpro/core/services/
    - build_orchestrator.py – Coordinates build tasks.
    - template_service.py – Loads and renders Jinja2 templates.
    - database_service.py – Manages SQLite DB interactions.
    - build_logger.py – Specialized logging for build processes.
- benchpro/core/ports/
    - executor.py – Defines the Executor interface.
- benchpro/infrastructure/
    - local_executor.py – Implements Executor locally.
    - (Future) slurm_executor.py – HPC-specific execution logic.
- benchpro/cli/
    - Where Click commands are defined (e.g., build, run, status).
- templates/
    - YAML configs (e.g., build.yaml) and Jinja2 templates (e.g., build.j2).
- tests/
    - Unit and integration tests. (Structure may vary.)



#7. Tips for Working with BenchPRO 2.0
##7.1 Reading the Domain Models First: Understanding task.py, job.py, and job_resources.py helps clarify HPC-specific workflows.

##7.2 Services Are Your Orchestrators: The domain objects remain “clean,” with only business rules. Services coordinate file I/O, logging, or HPC commands.

##7.3 Executors: If you’re implementing or debugging HPC submission logic, check the Executor interface and its concrete classes (LocalExecutor, future SlurmExecutor).

##7.4 Templates: Jinja2 allows advanced templating (loops, conditionals). Keep HPC scripts DRY by factoring out common patterns (e.g., resource directives) into partials or well-structured .j2 files.

##7.5 Testing:
- Start with pytest to confirm all unit tests pass.
- Check coverage to see if critical HPC logic is tested.
For HPC integration tests, you may need a real Slurm dev environment or robust mocks.



#8. Additional Resources
##8.1 Contribution Guide (coming soon!): Will detail how to write new services, add new domain objects, or create HPC executors for other schedulers.

##8.2 Design Docs (in docs/ if available): Any additional architecture diagrams or HPC environment references.



#9. Next Steps
- Fix Any Failing Tests: Stabilize the baseline.
- Implement SlurmExecutor: Key HPC scheduling feature.
- Enhance HPC Resource Validation: Prevent invalid requests from reaching the scheduler.
- Extend Dependency Handling: For multi-step HPC pipelines.
