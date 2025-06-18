# BenchPRO Developer Guide

This document provides a comprehensive overview of the BenchPRO codebase architecture, design patterns, and development conventions. It's designed to help new developers (both human and LLM) quickly understand the system and implement changes that align with existing conventions.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Design Patterns](#core-design-patterns)
3. [Module Structure](#module-structure)
4. [Configuration System](#configuration-system)
5. [Registry System](#registry-system)
6. [Executor System](#executor-system)
7. [Template System](#template-system)
8. [Workspace Management](#workspace-management)
9. [Development Patterns](#development-patterns)
10. [Testing Conventions](#testing-conventions)
11. [Common Development Tasks](#common-development-tasks)

## Architecture Overview

BenchPRO is an automated benchmarking utility built with a modular, composition-based architecture. The system follows these key principles:

- **Composition over Inheritance**: Components are composed together rather than using deep inheritance hierarchies
- **Interface-driven Design**: Clear interfaces define component contracts
- **Dependency Injection**: Components receive their dependencies as constructor parameters
- **Separation of Concerns**: Each module has a clear, focused responsibility

### High-Level Data Flow

```
CLI → ConfigManager → TaskOrchestrator → TaskFactory → Task → Components
                   ↓
              WorkspaceManager → RegistryManager → TemplateEngine → Execution
```

### Directory Structure

```
benchpro/
├── cli/                    # Command-line interface and user interaction
├── config/                 # Hierarchical configuration system
├── registry/               # Application registry management (currently completion-based)
├── executor/               # Task execution system (composition-based)
├── templates/              # Script generation and template system
├── workspace/              # Workspace and module management
├── results/                # Result capture and analysis
└── utils/                  # Shared utilities and helpers
```

## Core Design Patterns

### 1. Component Composition Pattern

The executor system uses composition instead of inheritance:

```python
class Task:
    def __init__(self, 
                 config_component: ConfigComponent,
                 validation_component: ValidationComponent,
                 script_generation_component: ScriptGenerationComponent,
                 execution_component: ExecutionComponent):
        # Components are injected as dependencies
```

### 2. Factory Pattern

Tasks are created using the Factory pattern with consistent dependency injection:

```python
class TaskFactory:
    def create_task(self, config: Dict[str, Any]) -> Task:
        # Creates tasks with proper component composition
```

### 3. Strategy Pattern

Execution components implement different execution strategies:

- `LocalExecutionComponent` - Local execution
- `SlurmExecutionComponent` - SLURM scheduler execution

### 4. Template Composition Pattern

Scripts are generated using composable template blocks:

```python
template_engine.compose([
    SHEBANG_BLOCK,
    SLURM_DIRECTIVES_BLOCK,
    MODULE_LOADING_BLOCK,
    # ... custom blocks
])
```

### 5. Configuration Hierarchical Merging

Configuration follows a hierarchical precedence system:
1. Default configuration (lowest precedence)
2. System configuration
3. Profile configuration
4. CLI overrides (highest precedence)

## Module Structure

### CLI Module (`benchpro/cli/`)

**Purpose**: Provides the command-line interface using Click framework.

**Key Files**:
- `cli.py` - Main CLI commands and orchestration
- `completion.py` - Shell completion functionality
- `commands/` - Additional command implementations

**Key Patterns**:
- Uses Click for command definition and parameter handling
- Integrates with ConfigManager for configuration loading
- Delegates execution to TaskOrchestrator

### Configuration Module (`benchpro/config/`)

**Purpose**: Manages hierarchical YAML configuration with tracking and validation.

**Key Files**:
- `config_manager.py` - Main configuration orchestrator
- `loader.py` - Configuration file loading
- `merger.py` - Hierarchical configuration merging
- `validator.py` - JSON schema-based validation
- `resolver.py` - Template variable resolution
- `metadata.py` - Configuration tracking and reporting

**Architecture**:
```python
ConfigManager
├── ConfigLoader (loads YAML files)
├── ConfigMerger (hierarchical merging with tracking)
├── VariableResolver (template variable resolution)
└── ConfigValidator (JSON schema validation)
```

**Key Patterns**:
- Component composition with dependency injection
- Comprehensive tracking of configuration sources and precedence
- Smart defaults application based on context

### Registry Module (`benchpro/registry/`)

**Purpose**: Manages application metadata and provides query interface.

**Key Files**:
- `registry_manager.py` - **CURRENTLY COMPLETION-BASED** registry operations
- `application_data.py` - Application data structures
- `registry_formatter.py` - Registry output formatting

**Current Architecture** (completion-based):
```python
RegistryManager
├── load() - File-based registry loading
├── save() - File-based registry persistence
├── register_application() - Registration only AFTER successful completion
└── find_applications() - Query completed applications only
```

**Key Operations**:
- Application registration with metadata (only for completed builds)
- Query interface with filtering (completed applications only)
- Module file creation integration

### Executor Module (`benchpro/executor/`)

**Purpose**: Composition-based task execution system.

**Key Files**:
- `task_orchestrator.py` - High-level task coordination
- `task_factory.py` - Task creation with component injection
- `task.py` - Base Task class and implementations (Application, Benchmark)
- `components/` - Execution, validation, and configuration components

**Component Architecture**:
```python
Task (composition-based)
├── ConfigComponent - Configuration management
├── ValidationComponent - Configuration validation
├── ScriptGenerationComponent - Template processing
└── ExecutionComponent - Job execution (Local/Slurm)
```

**Key Patterns**:
- Pure composition - no inheritance between task types
- Component interfaces define clear contracts
- Factory pattern for consistent task creation

### Template Module (`benchpro/templates/`)

**Purpose**: Composable script generation system.

**Key Files**:
- `blocks.py` - Template block abstractions
- `standard_blocks.py` - Standard template blocks (shebang, SLURM directives, etc.)
- `composition.py` - Template composition engine
- `script_generators.py` - Script generation components

**Block Composition**:
```python
# Standard blocks can be composed
script = compose_template([
    SHEBANG_BLOCK,
    SLURM_DIRECTIVES_BLOCK,
    MODULE_LOADING_BLOCK,
    custom_application_block,
    END_TIMESTAMP_BLOCK
])
```

### Workspace Module (`benchpro/workspace/`)

**Purpose**: Manages build workspaces and module files.

**Key Files**:
- `workspace_manager.py` - Workspace creation and management
- `module_manager.py` - Environment module file creation

**Responsibilities**:
- Creates isolated build workspaces
- Generates environment module files for applications
- Integrates with user directory management

## Configuration System

### Configuration Hierarchy

The configuration system follows a strict precedence order:

1. **Default Configuration** (`config/default.yaml`) - Base settings
2. **System Configuration** (`config/system/*.yaml`) - System-specific settings
3. **Profile Configuration** (user profiles) - Task-specific settings
4. **CLI Overrides** - Runtime parameter overrides

### Configuration Tracking

The system provides comprehensive tracking of configuration sources:

```python
config_report = config_manager.get_complete_config_report(profile_name, cli_overrides)
# config_report.config_metadata contains source tracking for each parameter
# config_report.merge_history contains step-by-step merge information
```

### Smart Defaults

Smart defaults are applied based on configuration context:

```python
# Example: If execution.type = "sched", automatically set job.scheduler = "slurm"
if execution_type == "sched" and not job.scheduler:
    smart_defaults["job"]["scheduler"] = "slurm"
```

### Validation

Configuration validation uses JSON schemas:

- `schema/application_schema.json` - Application task validation
- `schema/benchmark_schema.json` - Benchmark task validation

## Registry System

### Current Implementation (Completion-Based)

The registry system currently operates on a **completion-based model** that creates significant limitations for asynchronous execution:

**Current Behavior**:
- Registry entries are **only created after successful task completion**
- Failed tasks have **no registry presence**
- No tracking of in-progress tasks
- No integration with scheduler state checking

**File-Based Storage**:
- YAML-based registry file (`~/.benchpro/registry/registry.yaml`)
- File locking for concurrency control (`fcntl.flock`)

**Current Data Structure** (completed tasks only):
```yaml
version: "1.0"
last_updated: "2024-01-01T12:00:00Z"
applications:
  - id: "hello_world_10_abc123"
    name: "hello_world"
    version: "1.0"
    workspace_dir: "/path/to/workspace"
    binary_path: "/path/to/binary"
    environment:
      modules: ["gcc/11.2", "openmpi/4.1"]
    build_timestamp: "2024-01-01T12:00:00Z"
    status: "completed"  # Only completed tasks exist
```

### Architectural Challenge: Asynchronous Execution

**The Problem**:
With SLURM execution, tasks are inherently asynchronous but the registry system assumes synchronous completion:

1. **Task Submission**: BenchPRO submits a job to SLURM and gets a job ID
2. **Immediate Return**: Control returns to user while job runs asynchronously
3. **No Tracking**: No registry entry exists until completion
4. **State Ignorance**: No way to query job status or intermediate states

**Task Lifecycle States** (not currently tracked):
- `SUBMITTED` - Job submitted to scheduler
- `PENDING` - Job queued, waiting for resources
- `RUNNING` - Job actively executing
- `COMPLETED` - Job finished successfully
- `FAILED` - Job finished with errors
- `CANCELLED` - Job was cancelled
- `TIMEOUT` - Job exceeded time limit

**Required Capabilities** (not currently available):
- Track tasks from submission through completion
- On-demand job status queries via scheduler integration (e.g., `sacct`)
- Registry entries for all submitted tasks, regardless of state
- State-aware queries with real-time status determination
- Clean task lifecycle management

### Integration Points

**Current**:
- Application tasks register upon successful build
- Benchmark tasks query registry for completed applications only
- Module file creation integrated with registration

**Future Needs**:
- Registry creation at task submission
- State updates through job lifecycle
- Scheduler integration for status queries
- State-aware application dependency resolution

## Executor System

### Component Architecture

The executor uses a composition-based architecture with these components:

**Core Interfaces**:
```python
class ConfigComponent:
    def get_config() -> Dict[str, Any]
    def load_config(profile_name: str) -> Dict[str, Any]
    def merge_config(overrides: Dict[str, Any]) -> Dict[str, Any]

class ValidationComponent:
    def validate(config: Dict[str, Any]) -> Tuple[bool, List[str]]

class ExecutionComponent:
    def execute(script_path: str, workspace: Dict[str, Any]) -> Tuple[bool, str]
    def get_status(job_id: str) -> str
    def cancel_job(job_id: str) -> bool
```

**Task Implementations**:

```python
class Application(Task):
    # Handles application building and registry registration
    def run(self, is_local_execution: bool = True) -> Tuple[bool, Optional[str]]

class Benchmark(Task):
    # Handles benchmark execution with application dependencies
    def prepare(self, profile_name: str, cli_overrides: Dict[str, Any]) -> Dict[str, Any]
```

### Execution Flow

1. **TaskOrchestrator** coordinates the execution
2. **ConfigManager** loads and merges configuration
3. **WorkspaceManager** creates isolated workspace
4. **TaskFactory** creates task with appropriate components
5. **Task** generates script and submits job

## Template System

### Block-Based Composition

Templates are built using composable blocks:

```python
# Standard blocks available
SHEBANG_BLOCK = StringTemplateBlock("#!/bin/bash\n")
SLURM_DIRECTIVES_BLOCK = FileTemplateBlock("slurm_directives.j2")
MODULE_LOADING_BLOCK = FunctionTemplateBlock(generate_module_commands)
```

### Template Variables

Templates receive structured variables:

```python
template_variables = {
    "job": {
        "name": "job_name",
        "nodes": 1,
        "time": "01:00:00"
    },
    "application": {
        "binary_path": "/path/to/binary",
        "args": "input_args"
    },
    "environment": {
        "modules": ["gcc/11.2"],
        "variables": {"OMP_NUM_THREADS": "4"}
    }
}
```

## Workspace Management

### Directory Structure

Workspaces follow a consistent structure:

```
/path/to/workspace/
├── build/              # Build artifacts
├── logs/               # Job logs
├── scripts/            # Generated scripts
├── results/            # Output results
└── modules/            # Generated module files
```

### Module File Generation

Module files are created for environment management:

```tcl
#%Module1.0
proc ModulesHelp { } {
    puts stderr "Application: hello_world v1.0"
}

module-whatis "hello_world v1.0"
prepend-path PATH /path/to/workspace
setenv HELLO_WORLD_HOME /path/to/workspace
```

## Development Patterns

### Error Handling

Use specific exception types for clear error handling:

```python
from benchpro.executor.components.interfaces import ConfigError, ValidationError, ExecutionError

try:
    config = config_component.get_config()
except ConfigError as e:
    logger.error(f"Configuration error: {e}")
    raise
```

### Logging

Use the centralized logging system:

```python
from benchpro.utils.logger import get_logger

class MyComponent:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("Component initialized")
```

### Dependency Injection

Components should receive dependencies as constructor parameters:

```python
class MyComponent:
    def __init__(self, file_system: FileSystem, user_dir_manager: UserDirectoryManager):
        self.file_system = file_system
        self.user_dir_manager = user_dir_manager
```

### Interface Implementation

Implement clear interfaces for testability:

```python
class MyExecutionComponent(ExecutionComponent):
    def execute(self, script_path: str, workspace: Dict[str, Any]) -> Tuple[bool, str]:
        # Implementation here
        pass
```

## Testing Conventions

### Component Testing

Test components in isolation using dependency injection:

```python
def test_my_component():
    mock_file_system = Mock(spec=FileSystem)
    component = MyComponent(file_system=mock_file_system)
    # Test component behavior
```

### Integration Testing

Test component integration using real implementations:

```python
def test_task_execution():
    config_manager = ConfigManager()
    task_factory = TaskFactory(config_manager=config_manager)
    # Test integrated behavior
```

## Common Development Tasks

### Adding a New Execution Component

1. Implement the `ExecutionComponent` interface
2. Add component to the factory in `task_factory.py`
3. Update configuration schema if needed
4. Add tests for the new component

### Extending the Configuration System

1. Add new configuration parameters to schemas
2. Update default configuration if needed
3. Add validation rules
4. Update configuration tracking if new sources are added

### Adding Template Blocks

1. Create new block classes in `templates/blocks.py`
2. Register blocks in `standard_blocks.py` if they're standard
3. Update template composition logic
4. Add tests for new blocks

### Redesigning the Registry (Future State-Aware System)

Clean replacement of completion-based registry with on-demand state-aware system:

1. **Task Registration at Submission** - Create registry entries when jobs are submitted, not when completed
2. **On-Demand Status Determination** - Query scheduler status only when specifically requested
3. **Scheduler Integration** - Implement real-time status checking via scheduler APIs (e.g., `sacct` for SLURM)
4. **State-Aware Queries** - Allow filtering by job state with live status determination
5. **Clean Architecture** - Complete replacement of current system without compatibility layers

Example state-aware registry pattern:
```python
# Current (completion-based)
def register_application(self, app_data: Dict[str, Any]) -> str:
    # Only called after successful completion
    app_data["status"] = "completed"
    self.registry["applications"].append(app_data)

# Future (on-demand state-aware)
def register_task_submission(self, task_data: Dict[str, Any], job_id: str) -> str:
    # Called immediately upon job submission
    task_data["job_id"] = job_id
    task_data["submission_time"] = timestamp()
    # No status stored - determined on-demand
    self.registry["tasks"].append(task_data)

def get_task_status(self, task_id: str) -> str:
    # Called on-demand when status is needed
    task = self.find_task(task_id)
    if not task["job_id"]:
        return "UNKNOWN"
    
    # Query scheduler in real-time
    return self.scheduler_integration.get_job_status(task["job_id"])

def find_applications(self, criteria: Dict[str, Any], include_states: List[str] = ["COMPLETED"]) -> List[Dict[str, Any]]:
    # State-aware queries with on-demand status checking
    matching_tasks = []
    for task in self.registry["tasks"]:
        if matches_criteria(task, criteria):
            current_status = self.get_task_status(task["id"])
            if current_status in include_states:
                task["current_status"] = current_status  # Add for display
                matching_tasks.append(task)
    return matching_tasks

def list_all_tasks(self) -> List[Dict[str, Any]]:
    # For display tables - check status of each task on-demand
    tasks_with_status = []
    for task in self.registry["tasks"]:
        task_copy = task.copy()
        task_copy["current_status"] = self.get_task_status(task["id"])
        tasks_with_status.append(task_copy)
    return tasks_with_status
```

Key design principles:
- **No polling or background status updates** - scheduler load minimization
- **On-demand queries only** - status determined when explicitly requested
- **Clean break from current system** - no backwards compatibility constraints
- **Scheduler integration abstraction** - support multiple schedulers (SLURM, PBS, etc.)
- **Registry as submission log** - persistent record of all submitted tasks with metadata

This guide provides the foundation for understanding and extending BenchPRO's architecture while maintaining consistency with existing patterns and conventions. 