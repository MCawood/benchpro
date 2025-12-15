# BenchPRO 2.0

BenchPRO 2.0 is a deterministic benchmark orchestrator for HPC systems. It automates the process of building applications and running benchmarks, ensuring reproducibility and ease of use.

## Features
- **Automated Builds**: Compile applications from source with dependency management.
- **Benchmark Orchestration**: Schedule and execute benchmarks on HPC clusters (Slurm, etc.).
- **Reproducibility**: Capture all environment variables, compiler flags, and system state.
- **Hierarchical Configuration**: Flexible configuration with User, Site, and System layers.
- **Module Integration**: Seamless integration with Lmod for environment management.

## Getting Started

### For Users
BenchPRO is typically installed as a system module. To use it:

1. **Load the Module**
   ```bash
   module load benchpro
   ```

2. **Initialize**
   Run any command to automatically initialize your configuration:
   ```bash
   bp --version
   ```

3. **Run a Task**
   ```bash
   bp bench run --command "echo Hello World" --nodes 1
   ```

### For Site Maintainers
See [INSTALL.md](INSTALL.md) for instructions on how to deploy BenchPRO on your system.

## Documentation
- [Terminology](docs/terminology.md): Definitions of core concepts (Task, App, Benchmark, etc.).
- [Installation](INSTALL.md): Deployment guide.

## License
[License Information]
