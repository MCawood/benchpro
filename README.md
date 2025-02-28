# BenchPRO

BenchPRO is a benchmark execution and profiling tool designed for high-performance computing environments.

## Features

- **Simplified Configuration:** YAML-based configuration for global defaults, system contextualization, and application/benchmark profiles.
- **Modern Templating:** Job script rendering using Jinja2.
- **User-Friendly CLI:** Command-line interface built with Click.
- **Job Scheduler Abstraction:** Abstract interface for job submission with initial Slurm support.
- **Modular Build Executor:** Integration of configuration and templating for job generation and execution.
- **Result Capture:** Capture job output and provenance data.

## Installation

### Development Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/benchpro.git
   cd benchpro
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Usage

Basic usage examples:

```bash
# Build and submit a job
benchpro build --profile my_benchmark

# Check job status (future feature)
benchpro status --job-id 12345
```

## Project Structure

```
benchpro/
    cli/        - CLI implementation using Click
    config/     - YAML configuration files
    templates/  - Jinja2 templates for job scripts
    executor/   - Build executor and job scheduler abstraction
    results/    - Modules for capturing and querying results
    tests/      - Pytest unit and integration tests
    docs/       - Sphinx documentation files
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black benchpro
isort benchpro
```

## License

[MIT License](LICENSE) 