#1. Purpose
This document outlines how to contribute code to BenchPRO 2.0. For a broader understanding of the project’s architecture, design philosophy, and domain concepts, please refer to PROJECT_OVERVIEW.md.



#2. Prerequisites
##2.1 Python Environment
- We currently target Python 3.12+.
- Create a virtual environment and install development dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev,test]"
```

##2.2 Familiarity with DDD & Async
- The project uses a Domain-Driven Design approach.
- Many operations (like job execution) rely on async/await.



#3. Coding Standards
##3.1 Code Organization
- Domain-Driven Structure
    - Place core business logic in benchpro/core/domain/ (e.g., Task, Job, JobResources).
    - Add coordinating logic in benchpro/core/services/ (e.g., BuildOrchestrator, TemplateService).
    - New interfaces or ports go under benchpro/core/ports/, and their implementations belong in benchpro/infrastructure/ (e.g., local_executor.py, slurm_executor.py).
- Layer Boundaries
    - Domain objects should be as free of external dependencies as possible.
    - Services handle orchestration and call out to infrastructure via ports/adapters.

##3.2 Code Style
- Type Hints: Use them everywhere (python3 -m mypy or integrated tooling for checks).
- Async I/O: For HPC interactions and any blocking tasks, use async/await patterns.
- Logging & Error Handling:
    - Use structured logging where possible.
    - Raise or catch domain-specific exceptions for HPC or resource errors.

##3.3 Documentation
- Docstrings:
    - Use a consistent format (e.g., Google-style or Sphinx-compatible).
    - Each function or method should explain parameters, return types, and potential errors.
- In-Code Comments:
    - Provide brief, purpose-driven comments, especially around complex HPC logic.
- Project Docs:
    - For major changes or new modules, consider updating or adding a doc in docs/ to reflect new capabilities.



#4. Testing Strategy
##4.1 Test-First Approach
- Write tests before or alongside new code.
- We use pytest with optional pytest.mark.asyncio for async tests.

##4.2 Testing Layers
- Unit Tests: For domain objects (e.g., Job, Task) and core logic.
- Integration Tests: For orchestrators (e.g., BuildOrchestrator) and executors (LocalExecutor, future SlurmExecutor).
- CLI Tests: Where possible, use Click’s testing utilities (e.g., CliRunner).

##4.3 Mocking External Dependencies
- HPC or network calls should be mocked or stubbed in tests.
- For HPC job submission (e.g., Slurm), create mocks that simulate queue behavior.

##4.4 Coverage
- Aim for 80%+ coverage (or higher if feasible).
- Run pytest --cov=benchpro for coverage reports.



#5. Workflow & Pull Requests
##5.1 Development Branches
- Work on a dedicated feature/bugfix branch (feature/slurm-executor, bugfix/failing-tests, etc.).

##5.2 Commit Style
- Write clear, concise commit messages (subject + body).
- Reference relevant issues or tasks if applicable.

##5.3 Pull Request Checklist
- Ensure all tests pass locally (pytest).
- Check for consistent style with lint/mypy.
- Document any new or changed functionality in code docstrings and (if needed) docs/.

##5.4 Review Process
- A maintainer or core team member will review your PR.
- Address feedback, update the PR, and re-request a review.

##5.5 Post-Merge
- Confirm that the main branch CI passes.
- Update project docs (docs/) if the feature is user-facing.
- Monitor for issues or regressions.



#6. Guidelines for AI Assistants
##6.1 Scope Your Changes
- Make small, atomic PRs. Avoid mixing multiple features or refactors in a single submission.

##6.2 Testing & Validation
- Provide or update relevant tests.
- Validate that HPC logic doesn’t break existing jobs or tasks.

##6.3 Documentation
- Add docstrings describing any new domain concepts or HPC resource logic.



#7. Common Pitfalls
##7.1 Blocking Calls in Async Code
- Use async-friendly libraries or wrap blocking I/O in a thread executor.
- Don’t block the event loop (e.g., time.sleep).

##7.2 Overusing Global State
- Keep HPC environment or job submission context local to services or domain objects.
- Avoid hidden dependencies or cross-module globals.

##7.3 Incomplete Resource Validation
- HPC parameters (nodes, memory) should be validated upfront.
- Provide helpful error messages for invalid configs.

##7.4 Ignoring Long-Running Job Lifecycle
- HPC jobs can run for hours. Ensure state transitions account for timeouts or partial failures.



#8. Getting Started Quickly
##8.1 Clone & Install
```bash
git clone https://github.com/yourusername/benchpro.git
cd benchpro
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,test]"
```

##8.2 Run Tests
```bash
pytest
```

##8.3 Check Coverage & Style
```bash
pytest --cov=benchpro
mypy benchpro/
black --check benchpro/   # or isort/flake8 as configured
```

##8.4 Open a PR
Push your branch, open a pull request, and follow the checklist above.



#9. Further Information
 - For deeper details on BenchPRO’s domain concepts, HPC resource handling, and overall system design, see:

PROJECT_OVERVIEW.md – High-level architecture and domain models.
docs/ – Additional guides, user manuals, or architectural references.

Thanks for contributing to BenchPRO!

