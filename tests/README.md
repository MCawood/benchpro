# BenchPro 2.0 Testing System

This directory contains the comprehensive test suite for BenchPro 2.0, covering unit, integration, and end-to-end (E2E) testing scenarios.

## Quick Start

**Crucial**: You must install the package in **editable mode** for tests to run correctly. This adds the `src/` directory to your Python path, preventing `ModuleNotFoundError`.

```bash
# 1. Activate your virtual environment
source venv/bin/activate

# 2. Install package in editable mode (run from project root)
pip install -e .

# 3. Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# 4. Run all tests
pytest tests/
```

## Test Structure

The tests are organized into the following categories:

- **`unit/`**: Isolated tests for individual components (e.g., `core/domain.py`, `core/job_builder.py`). These mock external dependencies and run quickly.
- **`integration/`**: Tests checking the interaction between multiple components or with external systems (mocked or real), such as `core/executor.py` or database interactions.
- **`e2e/`**: End-to-End tests that treat the system as a black box, primarily using the CLI to run complete workflows.
- **`test_packaging.py`**: verifies installation and package structure.
- **`conftest.py`**: Global pytest fixtures (workspace setup, mocked schedulers, etc.).

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run by Category
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Check Coverage
We target >50% code coverage.
```bash
pytest --cov=benchpro --cov-report=term-missing tests/
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'benchpro'`
**Cause**: The project uses a `src/` layout, so `benchpro` is not in the default Python path.
**Fix**: Run `pip install -e .` in the project root. This creates a link to the source code that Python can follow.

### `RuntimeError: There is no current event loop`
**Cause**: Async tests running without an event loop fixture.
**Fix**: Ensure `pytest-asyncio` is installed and strict mode is handled, or use the `pytest.mark.asyncio` decorator. We also use `unittest.mock` to mock `asyncio.Semaphore` in synchronous unit tests to avoid this.
