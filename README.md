# BenchPRO

BenchPRO is an intelligent, system-agnostic benchmarking platform for Linux HPC systems that provides:
- AI-powered interface for benchmark execution and analysis
- Automatic system discovery and adaptation
- Comprehensive benchmark results with minimal user input
- Centralized database integration for result comparison
- Portable work units with complete provenance tracking

## Quick Start

### Installation

The BenchPRO package should already be installed on most TACC systems:

| System    | Module Path                              |
|-----------|------------------------------------------|
| Frontera  | /scratch1/hpc_tools/benchpro/modulefiles |
| Stampede2 | /scratch/hpc_tools/benchpro/modulefiles  |
| Lonestar6 | /scratch/projects/benchpro/modulefiles   |

1. Load BenchPRO on a login or staff node:
```bash
ml python3
ml use [module_path]
ml benchpro
```

2. Initialize workspace:
```bash
benchpro --validate
```

3. View system information:
```bash
benchpro --notices
benchpro --defaults
```

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/benchpro.git
cd benchpro
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[test,dev]"
```

4. Run tests:
```bash
pytest
```

## Documentation

- [Contributing Guide](CONTRIBUTING.md) - Development setup and guidelines
- [Project Roadmap](ROADMAP.md) - Development phases and future plans
- [Architecture](docs/architecture/) - System design and components
- [API Reference](docs/api/) - API documentation
- [User Guides](docs/guides/user/) - Usage instructions and examples
- [Developer Guides](docs/guides/development/) - Development best practices
- [Testing Guides](docs/guides/testing/) - Testing requirements and strategies

## License

This project is licensed under the MIT License - see the LICENSE file for details.
