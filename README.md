# BenchPRO 2.0

BenchPRO is a benchmark execution and profiling tool designed for high-performance computing environments. It simplifies the process of building applications, running benchmarks, and analyzing results.

## Features

- **Application Building**: Streamlined process for building applications with configurable parameters
- **Benchmark Execution**: Run benchmarks with customizable configurations
- **Job Scheduler Integration**: Support for various HPC job schedulers (currently Slurm)
- **Configuration Management**: Flexible YAML-based configuration system
- **Template-Based Job Scripts**: Generate job scripts using Jinja2 templates
- **Result Capture**: Collect and organize benchmark results

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/benchpro_2.0.git
cd benchpro_2.0

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Quick Start

### Building an Application

```bash
benchpro build-app --profile hello_world_app
```

### Running a Benchmark

```bash
benchpro run-benchmark --profile hello_world_bench
```

## Configuration

BenchPRO uses a layered configuration approach:

1. **Default Configuration**: Base settings for all jobs
2. **System Configuration**: System-specific settings
3. **Profile Configuration**: Task-specific settings
4. **CLI Overrides**: Command-line parameter overrides

Example application profile (`hello_world_app.yaml`):

```yaml
task_type: "application"
job:
  name: "hello_world_app"
  description: "Hello World application build"
application:
  name: "hello_world"
  source_dir: "examples/input/hello_world"
  build_script: "gcc -o hello_world hello_world.c"
  output_binary: "hello_world"
```

Example benchmark profile (`hello_world_bench.yaml`):

```yaml
task_type: "benchmark"
job:
  name: "hello_world_bench"
  description: "Hello World benchmark run"
benchmark:
  name: "hello_world"
  application: "hello_world"
  input_params: ""
```

## Project Structure

```
benchpro/
├── cli/                # Command-line interface
├── config/             # Configuration management
├── docs/               # Documentation
├── executor/           # Task execution system
├── registry/           # Application registry system
├── results/            # Result capture and analysis
├── templates/          # Template engine and templates
└── tests/              # Test suite
```

## Development

### Running Tests

```bash
python -m pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

See the [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) file for details on the development roadmap.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to all contributors who have helped shape BenchPRO
- Inspired by the needs of the HPC community 