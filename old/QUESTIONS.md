1. Domain & Architecture Questions

1.1 Domain Modeling

Which domain models do we have so far within benchpro/core/domain/?
For example, do we have a Build model, a Benchmark model, a Result model, etc.?

How do these domain objects relate to each other? (e.g., a Build references a set of Modules, or a Benchmark references a Build object.)
Are there any HPC-specific domain objects (e.g., HPCEnvironment, SchedulerConfig)?

1.2 Ports and Adapters

Could you clarify the interface definitions in benchpro/core/ports/?
Which infrastructure classes implement these interfaces? (e.g., SchedulerAdapter, ModuleSystemAdapter, etc.?)
Is the database (or data persistence) also handled via a port and an infrastructure adapter?

1.3 Services Layer

In the services/ folder, we see references like build_orchestrator.py, template_service.py, etc.
How do these services coordinate with the domain objects? For example, does BuildOrchestrator handle domain logic around building an application, or does it mostly orchestrate domain objects plus external calls (like Jinja rendering, environment detection)?

2. Configuration & Templates

2.1 YAML + Jinja2 Implementation

Could you show an example of the YAML configuration (e.g., build.yaml) and the corresponding Jinja template (build.j2)?
Do we now support loops, conditionals, or advanced templating constructs in the .j2 files for HPC job scripts?

2.2 Validation & Pydantic

Which Pydantic models are being used for the YAML config?
How granular is the validation? For instance, do we verify numeric ranges for HPC parameters like nodes, ranks, threads, etc.?

2.3 Scheduler Integration

How do we handle HPC parameters in 2.0 (e.g., do we parse them into a single object, or are they spread across multiple config sections)?
Have we accounted for HPC environment modules in the new code—i.e., is there a place in the domain or service layer that specifically references module loading?

3. CLI & User Interaction

3.1 Click Commands

Which Click commands exist so far? (e.g., benchpro build, benchpro run, benchpro capture)
How are we grouping them (e.g., one top-level command with subcommands vs. multiple root commands)?
Are we planning to unify or rename legacy commands (--build, --bench, etc.)?

3.2 Error Messaging & Rich Integration

How do we leverage Rich for status messages, progress bars, or highlighting HPC resource details?
Is there any structured way to display logs or errors so that users can easily debug HPC job failures?

3.3 Async/Await

The summary mentions async/await for I/O. How does that manifest in a CLI tool where HPC jobs are typically submitted and polled?
Do we have an async approach for waiting on HPC job completions or reading logs?

4. Testing & Quality

4.1 Testing Strategy

How are we structuring pytest tests? For instance, do we have separate tests/unit, tests/integration, tests/e2e directories?
Are we mocking HPC interactions (e.g., Slurm commands, environment module queries) or do we rely on a real HPC environment in CI?

4.2 Test Coverage & CI

Do we have a coverage target (e.g., 80%)?
Is there a CI pipeline (GitHub Actions, GitLab CI, etc.) running the tests automatically?

4.3 Error Handling & Logging

Does the system have a consistent approach to raising exceptions (custom domain exceptions vs. standard Python exceptions)?
How does build_logger.py integrate with the rest of the logging in the codebase (e.g., logging module vs. custom solution)?

5. Future Plans & Roadmap

5.1 Portability

Are we planning to abstract the HPC environment detection so we can support new HPC centers easily?
Is there a roadmap item for supporting other schedulers (e.g., PBS, LSF) or is that out of scope for the immediate future?

5.2 Reproducibility & Metadata

How do we plan to store build and benchmark metadata in the new 2.0 design? (Even if the database is still vague, do we have domain objects or data models for it?)
Will we consider new features like version stamping for the Python environment, dependencies, or container-based runs?

5.3 Integration with 1.0

Any plan to migrate existing 1.0 data or results, or is this strictly a clean break?
