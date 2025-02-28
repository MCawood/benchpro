# BenchPRO 2.0 Implementation Plan

## Current Status (Phase 1 Complete)

We have successfully implemented the core architecture for BenchPRO 2.0, which includes:

### Core Components
- **Configuration Management**: YAML-based configuration system with support for defaults, system configs, and profiles
- **Template Engine**: Jinja2-based template rendering for job scripts
- **Job Scheduler Abstraction**: Interface for job submission with Slurm implementation
- **Task System**: Hierarchy of task types (Application, Benchmark) with common base functionality
- **Build Executor**: Integration of configuration, templating, and job submission
- **CLI Interface**: User-friendly commands for building applications and running benchmarks
- **Result Capture**: Basic functionality for capturing job results

### Examples
- Hello World application build and benchmark run
- Integration tests that validate the complete workflow

### Testing
- Unit tests for individual components
- Integration tests for end-to-end workflows
- Test fixtures that create realistic test environments

## Phase 2 Roadmap

### Application Registry System
- [ ] **Core Registry Implementation**
  - [ ] Create `RegistryManager` class for managing application metadata
  - [ ] Implement YAML-based registry storage with version tracking
  - [ ] Add CRUD operations (create, read, update, delete) for application entries
  - [ ] Implement query interface for finding applications by criteria
  - [ ] Add registry persistence with concurrency handling

- [ ] **Application Integration**
  - [ ] Update `Application` class to register builds upon completion
  - [ ] Extend application profiles with version and metadata fields
  - [ ] Add build parameter tracking (compiler, flags, etc.)
  - [ ] Implement binary path resolution and validation

- [ ] **Benchmark Integration**
  - [ ] Update `Benchmark` class to query registry for application binaries
  - [ ] Add application selection criteria to benchmark profiles
  - [ ] Modify templates to use registry-provided binary paths
  - [ ] Implement fallback mechanisms for backward compatibility

- [ ] **CLI Extensions**
  - [ ] Add `registry` command group for managing the application registry
  - [ ] Implement subcommands: list, info, remove, clean
  - [ ] Add registry status reporting and validation

- [ ] **Testing Framework**
  - [ ] Create test fixtures for registry testing
  - [ ] Add unit tests for `RegistryManager`
  - [ ] Implement integration tests for application-benchmark relationships
  - [ ] Test error handling and edge cases

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

### Documentation
- [ ] Comprehensive user guide
- [ ] Developer documentation
- [ ] Example gallery

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
1. **Phase 1**: Core Registry Implementation
2. **Phase 2**: Application Integration
3. **Phase 3**: Benchmark Integration
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
│   ├── build_executor.py  # Main executor
│   ├── scheduler.py    # Job scheduler abstraction
│   └── task.py         # Task hierarchy
├── registry/           # Application registry system
│   ├── registry_manager.py  # Registry management
│   └── models.py       # Data models for registry entries
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
