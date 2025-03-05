# BenchPRO 2.0 Implementation Plan

## Current Status (Phase 2 In Progress)

We have successfully implemented the core architecture for BenchPRO 2.0, which includes:

### Core Components
- **Configuration Management**: YAML-based configuration system with support for defaults, system configs, and profiles
- **Template Engine**: Jinja2-based template rendering for job scripts
- **Job Scheduler Abstraction**: Interface for job submission with Slurm implementation
- **Task System**: Hierarchy of task types (Application, Benchmark) with common base functionality
- **Build Executor**: Integration of configuration, templating, and job submission
- **CLI Interface**: User-friendly commands for building applications and running benchmarks
- **Result Capture**: Basic functionality for capturing job results
- **Shell Completion**: Auto-completion for commands and options in Bash and Zsh shells

### Registry System (Implemented)
- **Core Registry Implementation**
  - [x] Create `RegistryManager` class for managing application metadata
  - [x] Implement YAML-based registry storage with version tracking
  - [x] Add CRUD operations (create, read, update, delete) for application entries
  - [x] Implement query interface for finding applications by criteria
  - [x] Add registry persistence with concurrency handling

- **Application Integration**
  - [x] Update `Application` class to register builds upon completion
  - [x] Extend application profiles with version and metadata fields
  - [x] Add build parameter tracking (compiler, flags, etc.)
  - [x] Implement binary path resolution and validation

- **Benchmark Integration**
  - [x] Update `Benchmark` class to query registry for application binaries
  - [x] Add application selection criteria to benchmark profiles
  - [x] Modify templates to use registry-provided binary paths
  - [x] Implement fallback mechanisms for backward compatibility

### Workspace Management (Implemented)
- [x] Create `WorkspaceManager` class for managing workspace directories
- [x] Implement standardized directory structure for workspaces
- [x] Add support for workspace creation and cleanup
- [x] Integrate with task system for workspace management

### Examples
- Hello World application build and benchmark run
- Integration tests that validate the complete workflow

### Testing
- Unit tests for individual components
- Integration tests for end-to-end workflows
- Test fixtures that create realistic test environments

## Phase 2 Roadmap (Remaining Items)

### CLI Extensions
- [x] Add `registry` command group for managing the application registry
- [x] Implement subcommands: list, info, remove, clean
- [x] Add registry status reporting and validation
- [x] Add shell completion for commands and options
- [x] Streamline CLI commands (`build` instead of `build-app`, `bench` instead of `run-benchmark`)
- [x] Improve CLI usability by accepting profile names as arguments instead of options

### Enhanced Task System
- [ ] Add dependency tracking between applications and benchmarks
- [ ] Support for task chaining (e.g., build application → run benchmark)
- [ ] Task status tracking and resumption

### Scheduler Enhancements
- [ ] Add support for PBS/Torque scheduler
- [ ] Add support for LSF scheduler
- [ ] Implement scheduler auto-detection

### Result Analysis
- [ ] Enhanced result capture with structured data
- [ ] Result comparison across benchmark runs
- [ ] Performance visualization

### User Experience
- [ ] Interactive CLI with progress indicators
- [ ] Web-based dashboard for monitoring jobs
- [ ] Configuration validation with helpful error messages

## Phase 3 Roadmap (Future Development)

### Revised Templating System
- [ ] **Configuration System Updates**
  - [ ] Create new configuration schema with logical sections
  - [ ] Implement variable substitution within configuration values
  - [ ] Add support for environment variables in configuration
  - [ ] Create validation system for configuration files

- [ ] **Template System Enhancements**
  - [ ] Create base templates with template inheritance
  - [ ] Implement block-based template composition
  - [ ] Create application-specific templates that extend base templates
  - [ ] Add support for conditional template sections
  - [ ] Develop template validation and error reporting

- [ ] **Environment Management**
  - [ ] Implement environment variable handling in templates
  - [ ] Add support for module loading and environment setup
  - [ ] Create system for propagating environment between build and run phases
  - [ ] Support for compiler-specific environment variables

### Advanced Features
- [ ] **Dependency Management**
  - [ ] Track dependencies between applications and benchmarks
  - [ ] Implement automatic rebuilding of dependencies
  - [ ] Add support for version constraints

- [ ] **Performance Analysis**
  - [ ] Implement performance data collection
  - [ ] Add support for performance visualization
  - [ ] Create performance comparison tools

- [ ] **Containerization**
  - [ ] Add support for containerized applications
  - [ ] Implement container registry integration
  - [ ] Create container-based execution environments

### Documentation
- [ ] Comprehensive user guide
- [ ] Developer documentation
- [ ] Example gallery

## Suggested Development Avenues

Based on the current state of the codebase and the implementation plan, here are some suggested avenues for development:

1. **CLI Extensions for Registry Management**
   - Implement CLI commands for managing the registry
   - Add support for listing, querying, and removing registry entries
   - Create user-friendly output formats for registry information
   - ✅ Add shell completion for commands and options

2. **Task Chaining and Dependency Tracking**
   - Enhance the task system to support dependencies between tasks
   - Implement automatic execution of dependent tasks
   - Add support for task status tracking and resumption

3. **Additional Scheduler Support**
   - Implement support for PBS/Torque and LSF schedulers
   - Create scheduler auto-detection mechanism
   - Add scheduler-specific template customizations

4. **Result Analysis and Visualization**
   - Enhance result capture with structured data
   - Implement result comparison across benchmark runs
   - Create visualization tools for performance data

5. **Template System Enhancements**
   - Implement template inheritance for more modular templates
   - Create base templates with common functionality
   - Add support for conditional template sections

6. **Pydantic Migration**
   - Address the Pydantic deprecation warnings
   - Migrate from V1-style validators to V2-style field validators
   - Update configuration schemas to use ConfigDict instead of class-based config

7. **Error Handling and User Experience**
   - Improve error messages and error handling
   - Add progress indicators for long-running operations
   - Implement interactive CLI features

8. **Documentation and Examples**
   - Create comprehensive user documentation
   - Add developer guides for extending the system
   - Create example applications and benchmarks

## Registry Implementation Details

### Registry Data Structure
```yaml
# Example registry.yaml structure
version: "1.0"
last_updated: "2025-02-28T11:40:27Z"
applications:
  - id: "hello_world_1740764294_dixs3a"
    name: "hello_world"
    version: "1.0"
    build_timestamp: "2025-02-28T11:38:26Z"
    status: "completed"
    workspace_dir: "examples/output/hello_world_app_1740764294_dixs3a"
    binary_path: "examples/output/hello_world_app_1740764294_dixs3a/build/hello_world"
    build_parameters:
      compiler: "gcc"
      flags: "-O2"
    metadata:
      description: "Simple Hello World application"
      tags: ["example", "tutorial"]
```

### Registry Manager Class Structure
```
RegistryManager
├── __init__(registry_path=None)
├── load()
├── save()
├── register_application(app_data)
├── update_application(app_id, app_data)
├── remove_application(app_id)
├── find_application(app_id)
├── find_applications(criteria)
├── get_binary_path(app_id)
├── list_applications()
└── clean_registry()
```

### Integration Points
1. **Application Build Process**: Register applications after successful builds
2. **Benchmark Execution Process**: Query registry for application binaries
3. **Template Modifications**: Update templates to use binary paths from registry
4. **CLI Interface**: Add commands to manage the registry

### Configuration Updates
- **Application Profile Updates**: Add version and metadata fields
- **Benchmark Profile Updates**: Add application selection criteria

### Implementation Phases
1. **Phase 1**: Core Registry Implementation (Completed)
2. **Phase 2**: Application Integration (Completed)
3. **Phase 3**: Benchmark Integration (Completed)
4. **Phase 4**: Advanced Features (cleanup, dependency tracking, variants)

### Future Extensions
1. **Spack Integration**: Support for Spack-built applications
2. **Advanced Querying**: Complex queries with multiple criteria
3. **Performance Tracking**: Track benchmark performance with specific applications

## Directory Structure

```
benchpro/
├── cli/                # Command-line interface
├── config/             # Configuration management
├── docs/               # Documentation
├── executor/           # Task execution system
│   ├── task_orchestrator.py  # Main orchestrator
│   ├── task_base.py    # Base task class
│   ├── application_task.py  # Application task
│   ├── benchmark_task.py  # Benchmark task
│   ├── task_factory.py  # Task factory
│   ├── scheduler.py    # Job scheduler abstraction
│   └── executor.py     # Execution engine
├── registry/           # Application registry system
│   └── registry_manager.py  # Registry management
├── workspace/          # Workspace management
│   └── workspace_manager.py  # Workspace management
├── results/            # Result capture and analysis
├── templates/          # Template engine and templates
└── tests/              # Test suite
```

## Development Guidelines

1. **Modularity**: Keep components loosely coupled
2. **Testing**: Write tests for all new functionality
3. **Documentation**: Update docs as code evolves
4. **Error Handling**: Provide helpful error messages
5. **Backward Compatibility**: Maintain compatibility with existing profiles

## Implementation Notes

- The Task hierarchy (Task → Application/Benchmark) is the central architectural pattern
- TaskFactory creates the appropriate task type based on configuration
- Configuration follows a layered approach (defaults → system → profile → CLI)
- Templates are specialized for different task types
- The Registry system creates a formal relationship between applications and benchmarks
- Applications are registered upon successful build and discovered by benchmarks at runtime
- Workspace management provides standardized directory structures for tasks

## Revised Templating System

### Overview
The revised templating system aims to improve upon the current YAML/J2 implementation. It will provide a more intuitive, maintainable, and error-resistant way to define application builds and benchmark runs while reducing duplication and improving portability.

### Key Design Principles
1. **Separation of Concerns**: Clearly separate configuration parameters from application-specific build steps
2. **Reduced Duplication**: Eliminate redundant configuration through smart defaults and derived values
3. **Improved Portability**: Remove hard-coded paths and system-specific references
4. **Logical Organization**: Structure configuration into meaningful sections
5. **Error Prevention**: Validate configuration and provide helpful error messages

### Configuration Structure
```yaml
# Example of revised application configuration
name: "hello_world"
version: "1.0"
description: "Simple Hello World application"

# Build configuration (parameters used by the template)
build:
  source: "hello_world.c"
  compiler: "gcc"
  flags: "-O2"
  output: "hello_world"
  threads: 4

# Template specification
template: "hello_world.j2"  # Application-specific template

# Environment configuration
environment:
  modules:
    - "gcc/11.2.0"
  variables:
    OMP_NUM_THREADS: "4"
    MKL_NUM_THREADS: "4"

# Job configuration
job:
  scheduler: "slurm"
  queue: "compute"
  nodes: 1
  tasks_per_node: 1
  time_limit: "00:10:00"
```

### Template Structure
Application-specific templates contain the unique build steps for each application:

```jinja
{# Application-specific template for Hello World #}
{# This extends the base application template #}
{% extends "base/application.j2" %}

{# Override the build_steps block #}
{% block build_steps %}
echo "Building application: {{ name }} {{ version }}"

# Compile the application
{{ build.compiler }} {{ build.flags }} -o {{ build.output }} {{ build.source }}

# Copy output to build directory
mkdir -p {{ workspace.build_dir }}
cp {{ build.output }} {{ workspace.build_dir }}/
{% endblock %}
```

Base template that handles common elements:

```jinja
{# Base template for all applications #}
#!/bin/bash
{# Scheduler directives #}
#SBATCH --job-name={{ job.name }}
#SBATCH --output={{ workspace.logs_dir }}/{{ job.name }}_%j.out
#SBATCH --error={{ workspace.logs_dir }}/{{ job.name }}_%j.err
#SBATCH --time={{ job.time_limit }}
#SBATCH --nodes={{ job.nodes }}
#SBATCH --ntasks-per-node={{ job.tasks_per_node }}
{% if job.queue %}
#SBATCH --partition={{ job.queue }}
{% endif %}
{% if job.account %}
#SBATCH --account={{ job.account }}
{% endif %}

# Job Information
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: {{ name }}"
echo "Nodes: $SLURM_JOB_NODELIST"
echo "Start Time: $(date)"

# Environment setup
{% if environment.modules %}
# Load modules
{% for module in environment.modules %}
module load {{ module }}
{% endfor %}
{% endif %}

{% if environment.variables %}
# Set environment variables
{% for key, value in environment.variables.items() %}
export {{ key }}="{{ value }}"
{% endfor %}
{% endif %}

# Change to source directory
cd {{ workspace.source_dir }}

{# Application-specific build steps #}
{% block build_steps %}
# This block will be overridden by application-specific templates
{% endblock %}

echo "End Time: $(date)"
echo "Application build completed successfully"
```
