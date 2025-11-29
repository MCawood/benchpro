# BenchPRO-NG

**BenchPRO-NG** (Next Generation) is a deterministic, extensible benchmark orchestrator for High Performance Computing (HPC) environments. It simplifies the process of building applications, defining benchmark suites, and executing them across diverse systems (local, Slurm, etc.) with strict reproducibility and provenance.

## Core Philosophy

*   **Determinism**: Every task execution is fully defined by its configuration. No hidden state.
*   **Separation of Concerns**:
    *   **Builds**: Compiling applications (e.g., LAMMPS, WRF) is decoupled from running them.
    *   **Suites**: Benchmark definitions are decoupled from the system they run on.
    *   **Results**: Provenance and metrics are captured in a structured local store (SQLite).
*   **Layered Configuration**: Defaults < Site < System < User < Task.

## Installation

BenchPRO-NG requires Python 3.9+.

```bash
# Clone the repository
git clone git@github.com:MCawood/benchpro.git
cd benchpro

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

BenchPRO-NG provides a unified CLI tool: `bp`.

### 1. Run a Single Task
Execute a simple command immediately without a suite file.

```bash
# Run a local echo command
bp task run "echo 'Hello BenchPRO'" --nodes 1

# Run with resource requests
bp task run "hostname" --nodes 2 --ranks 4 --system slurm
```

### 2. Build an Application
Define how to build your application using a YAML config and a Jinja2 template.

**`app.yaml`**:
```yaml
name: pi_calc
version: "1.0"
source: "src/pi.c"
build_template: "build.sh.j2"
compiler: "gcc"
```

**Run the build**:
```bash
bp build run app.yaml
```
This compiles the app and registers it in the local database.

### 3. Run a Benchmark Suite
Define a suite of tasks using a matrix of parameters.

**`suite.yaml`**:
```yaml
name: pi_scaling
requirements:
  code: pi_calc
  version: "1.0"

matrix:
  params:
    iterations: [1000, 2000, 4000]

resources:
  nodes: 1
  threads: 4

command: "pi_calc ${iterations}"
```

**Run the suite**:
```bash
bp suite run suite.yaml
```

### 4. Analyze Results
View the status and output of your runs.

```bash
# List all runs
bp results list

# Show details of a specific run
bp results show <run_id>
```

## Key Concepts

### Tasks
A **Task** is the atomic unit of work. It consists of a command, resource requirements (nodes, ranks, etc.), and an environment. Tasks are executed by an **Executor** (Local or Slurm).

### Builds
A **Build** represents a compiled application. BenchPRO manages the compilation process and stores metadata (compiler, flags, timestamp). Tasks can bind to specific builds using `requirements`.

### Suites
A **Suite** is a collection of tasks generated from a configuration matrix. The **Planner** expands the matrix into individual tasks.

### ResultStore
The **ResultStore** is a local SQLite database that records every run, task, and build. It ensures you never lose track of what you ran and how.

## Development

### Running Tests
We use `pytest` for testing.

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests
pytest -m integration
```

### Project Structure
*   `src/benchpro/core`: Core logic (Planner, Executor, Resolver, etc.).
*   `src/benchpro/cli`: CLI implementation (Click-based).
*   `tests/`: Comprehensive test suite.
*   `examples/`: Sample configurations and templates.

## Contributing
1.  Fork the repository.
2.  Create a feature branch.
3.  Write tests for your changes.
4.  Submit a Pull Request.
