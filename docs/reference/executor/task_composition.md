# Task Composition Architecture

BenchPRO's task architecture has been refactored to use composition over inheritance, providing more flexibility, testability, and extensibility.

## Overview

The composition-based architecture breaks down tasks into smaller, more focused components that each handle a specific responsibility. This allows for:

- **Flexibility**: Components can be swapped out independently of one another
- **Testability**: Components can be tested in isolation with mock dependencies
- **Extensibility**: New components can be added without modifying existing code
- **Reusability**: Components can be shared across different task types

## Key Components

The task architecture consists of several key component types:

### 1. Configuration Components

Components that handle loading and managing task configuration:

- `BaseConfigComponent`: Common configuration functionality
- `ApplicationConfigComponent`: Application-specific configuration logic
- `BenchmarkConfigComponent`: Benchmark-specific configuration logic

These components handle loading configuration from YAML files, merging with CLI overrides, and providing access to configuration values.

### 2. Validation Components

Components that validate task configuration:

- `BaseValidationComponent`: Common validation logic
- `ApplicationValidationComponent`: Application-specific validation logic
- `BenchmarkValidationComponent`: Benchmark-specific validation logic

These components ensure that configurations contain required fields and values are valid.

### 3. Script Generation Components

Components that generate execution scripts:

- `LocalScriptGenerator`: Generates scripts for local execution
- `SlurmScriptGenerator`: Generates scripts for Slurm execution with appropriate directives

Both generators use the same template files but produce different scripts depending on the execution mode.

### 4. Execution Components

Components that execute scripts:

- `LocalExecutionComponent`: Executes scripts locally using subprocess
- `SlurmExecutionComponent`: Submits scripts to Slurm using the scheduler

These components handle running scripts, monitoring execution, and retrieving results.

## Task Classes

The task classes have been refactored to use these components:

### `Task` (Base Class)

The base Task class now accepts components in its constructor and delegates behavior to them:

```python
class Task:
    def __init__(self, 
                 config_component,
                 validation_component,
                 script_generation_component,
                 execution_component):
        self.config_component = config_component
        self.validation_component = validation_component
        self.script_generation_component = script_generation_component
        self.execution_component = execution_component
        
    def prepare(self, config_path, cli_overrides=None):
        # Load and validate configuration using components
        config = self.config_component.load_config(config_path)
        if cli_overrides:
            config = self.config_component.merge_config(cli_overrides)
        is_valid, errors = self.validation_component.validate(config)
        # ...
        
    def generate_script(self, template_path, output_path):
        # Generate script using components
        config = self.config_component.get_config()
        variables = self.script_generation_component.prepare_variables(config)
        script_content = self.script_generation_component.generate_script(template_path, variables)
        # ...
        
    def submit_job(self, script_path):
        # Submit job using components
        success, job_id = self.execution_component.execute(script_path)
        # ...
```

### `Application` and `Benchmark` Classes

The Application and Benchmark classes extend the Task base class with additional functionality specific to their needs. They use the same component-based approach, with components specialized for their requirements.

## Task Factory

The `TaskFactoryComposition` handles creating tasks with the appropriate components:

```python
class TaskFactoryComposition:
    def create_task(self, task_type, execution_type=None, config=None):
        # Determine execution type from config if not specified
        if execution_type is None and config:
            execution_type = config.get('execution', {}).get('type', 'local')
            
        # Create components based on task type and execution type
        config_component = self._create_config_component(task_type)
        validation_component = self._create_validation_component(task_type)
        script_gen_component = self._create_script_generation_component(execution_type)
        execution_component = self._create_execution_component(execution_type)
        
        # Create and return the task instance
        if task_type == "application":
            return Application(...)
        elif task_type == "benchmark":
            return Benchmark(...)
```

The factory takes care of creating and wiring up the correct components based on the task type and execution type.

## Usage Example

Here's how to use the composition-based architecture:

```python
# Create a task factory
factory = TaskFactoryComposition()

# Create an application task with local execution
app_task = factory.create_task("application", "local")

# Prepare the task with a configuration file
config = app_task.prepare("path/to/config.yaml")

# Generate a script
script_path = app_task.generate_script("path/to/template.j2", "output/script.sh")

# Submit the job
success, job_id = app_task.submit_job(script_path)

# Check the status of the job
status = app_task.get_job_status(job_id)
```

You can also create a task with Slurm execution:

```python
# Create a benchmark task with Slurm execution
bench_task = factory.create_task("benchmark", "slurm")

# The rest of the API is the same
config = bench_task.prepare("path/to/config.yaml")
script_path = bench_task.generate_script("path/to/template.j2", "output/script.sh")
success, job_id = bench_task.submit_job(script_path)
```

## YAML Configuration

The execution type can be specified in the YAML configuration:

```yaml
# Set execution type to sched
execution:
  type: sched
  
# Job configuration (used for Slurm directives)
job:
  name: benchmark_job
  nodes: 2
  tasks_per_node: 16
  time_limit: 01:00:00
  queue: normal
  account: myproject
```

When using Slurm execution, the `job` section is used to generate Slurm directives automatically.

## Benefits over Inheritance

The composition-based architecture offers several advantages over the inheritance-based approach:

1. **Separation of Concerns**: Each component handles a specific responsibility, making the code more modular and easier to understand.

2. **Dependency Injection**: Components can be injected, making it easy to substitute different implementations for testing or special cases.

3. **Reduced Coupling**: Components interact through well-defined interfaces, reducing coupling between different parts of the system.

4. **Easier Testing**: Components can be tested in isolation with mock dependencies, simplifying testing.

5. **Flexible Configuration**: The behavior of tasks can be configured by selecting different component implementations.

## Migrating from Inheritance

If you have code that uses the inheritance-based Task classes, you can migrate to the composition-based architecture by:

1. Using the `TaskFactoryComposition` instead of the old `TaskFactory`
2. Passing the execution type when creating tasks
3. Using the same API methods (`prepare`, `generate_script`, `submit_job`)

The public API of the Task classes remains largely the same, facilitating a smooth transition. 