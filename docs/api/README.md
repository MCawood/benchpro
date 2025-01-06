# BenchPRO API Reference

## Core Domain

### Task

The `Task` class represents a unit of work to be executed.

```python
from uuid import UUID
from pathlib import Path
from typing import Dict, List

class Task:
    def __init__(self, id: UUID, name: str, working_dir: Path, template_path: Path, variables: Dict):
        """
        Initialize a new task.

        Args:
            id: Unique identifier for the task
            name: Human-readable name
            working_dir: Directory for task execution
            template_path: Path to job template
            variables: Template variables
        """
        pass

    def validate(self) -> List[str]:
        """
        Validate task configuration.

        Returns:
            List of validation errors, empty if valid
        """
        pass

    def transition_to(self, new_status: 'TaskStatus'):
        """
        Change task state.

        Args:
            new_status: New status to transition to

        Raises:
            InvalidStateTransition: If transition is not allowed
        """
        pass

    @property
    def status(self) -> 'TaskStatus':
        """Get current task status."""
        pass
```

### Job

The `Job` class represents a running task instance.

```python
class Job:
    def __init__(self, task: Task, executor: 'Executor'):
        """
        Initialize a new job.

        Args:
            task: Task to execute
            executor: Executor handling the job
        """
        pass

    @property
    def status(self) -> 'JobStatus':
        """Get current job status."""
        pass

    def cancel(self):
        """Request job cancellation."""
        pass
```

## Execution Framework

### Executor

Base class for task execution implementations.

```python
from abc import ABC, abstractmethod

class Executor(ABC):
    @abstractmethod
    async def submit(self, task: Task) -> Job:
        """
        Submit a task for execution.

        Args:
            task: Task to execute

        Returns:
            Job instance tracking execution

        Raises:
            TaskExecutionError: If submission fails
        """
        pass

    @abstractmethod
    async def wait(self, job: Job) -> 'Result':
        """
        Wait for job completion.

        Args:
            job: Job to wait for

        Returns:
            Execution result

        Raises:
            TaskExecutionError: If execution fails
        """
        pass

    @abstractmethod
    async def cancel(self, job: Job):
        """
        Cancel a running job.

        Args:
            job: Job to cancel

        Raises:
            TaskExecutionError: If cancellation fails
        """
        pass
```

### LocalExecutor

Local system task executor implementation.

```python
class LocalExecutor(Executor):
    async def submit(self, task: Task) -> Job:
        """Submit task for local execution."""
        pass

    async def wait(self, job: Job) -> 'Result':
        """Wait for local job completion."""
        pass

    async def cancel(self, job: Job):
        """Cancel local job."""
        pass
```

## Resource Management

### TaskResources

Resource requirements and tracking.

```python
class TaskResources:
    def __init__(self, cpu_cores: int, memory_gb: float, gpu_count: int = 0):
        """
        Initialize resource requirements.

        Args:
            cpu_cores: Number of CPU cores
            memory_gb: Memory in gigabytes
            gpu_count: Number of GPUs (optional)
        """
        pass

    def validate(self) -> bool:
        """
        Validate resource requirements.

        Returns:
            True if valid, False otherwise
        """
        pass

    @property
    def total_memory(self) -> int:
        """Get total memory in megabytes."""
        pass
```

## Configuration

### Config

System and user configuration management.

```python
class Config:
    @classmethod
    def from_file(cls, path: str) -> 'Config':
        """
        Load configuration from file.

        Args:
            path: Path to config file

        Returns:
            Config instance

        Raises:
            ConfigError: If loading fails
        """
        pass

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if valid, False otherwise
        """
        pass

    def get_executor_config(self) -> Dict:
        """Get executor configuration."""
        pass

    def get_template_config(self) -> Dict:
        """Get template configuration."""
        pass
```

## Templates

### Template

Job template management and rendering.

```python
class Template:
    @classmethod
    def load(cls, path: str) -> 'Template':
        """
        Load template from file.

        Args:
            path: Path to template file

        Returns:
            Template instance

        Raises:
            TemplateError: If loading fails
        """
        pass

    def render(self, variables: Dict) -> str:
        """
        Render template with variables.

        Args:
            variables: Template variables

        Returns:
            Rendered template string

        Raises:
            TemplateError: If rendering fails
        """
        pass

    def validate(self) -> List[str]:
        """
        Validate template syntax.

        Returns:
            List of validation errors, empty if valid
        """
        pass
```

## CLI Interface

### Task Commands

```python
@click.group()
def task():
    """Task management commands."""
    pass

@task.command()
@click.option('--name', required=True, help='Task name')
@click.option('--template', required=True, help='Template path')
def create(name: str, template: str):
    """Create a new task."""
    pass

@task.command()
@click.argument('task_name')
def run(task_name: str):
    """Run a task."""
    pass

@task.command()
@click.argument('task_name')
def status(task_name: str):
    """Get task status."""
    pass
```

### Template Commands

```python
@click.group()
def template():
    """Template management commands."""
    pass

@template.command()
@click.argument('name')
def create(name: str):
    """Create a new template."""
    pass

@template.command()
@click.argument('name')
def validate(name: str):
    """Validate template syntax."""
    pass
```

## Error Handling

### Custom Exceptions

```python
class BenchProError(Exception):
    """Base class for all BenchPRO exceptions."""
    pass

class TaskExecutionError(BenchProError):
    """Raised when task execution fails."""
    pass

class ResourceError(BenchProError):
    """Raised when resource allocation fails."""
    pass

class ConfigError(BenchProError):
    """Raised when configuration is invalid."""
    pass

class TemplateError(BenchProError):
    """Raised when template processing fails."""
    pass
```

## Template System

### TemplateLoader

Handles template discovery and loading.

```python
class TemplateLoader:
    def __init__(self, template_dir: Path):
        """
        Initialize template loader.

        Args:
            template_dir: Root directory for templates
        """
        pass

    def load_config(self, name: str) -> TemplateConfig:
        """
        Load template configuration.

        Args:
            name: Template name

        Returns:
            Template configuration

        Raises:
            TemplateNotFoundError: Template not found
            TemplateConfigError: Invalid configuration
        """
        pass

    def load_template(self, name: str, template_file: str) -> str:
        """
        Load template file content.

        Args:
            name: Template name
            template_file: Template file name

        Returns:
            Template content

        Raises:
            TemplateNotFoundError: Template not found
            TemplateValidationError: Invalid template
        """
        pass

    def list_applications(self) -> List[str]:
        """
        List available application templates.

        Returns:
            List of template names
        """
        pass

    def list_benchmarks(self) -> List[str]:
        """
        List available benchmark templates.

        Returns:
            List of template names
        """
        pass
```

### TemplateConfig

Manages template configuration and validation.

```python
class TemplateConfig:
    def __init__(self, config: Dict):
        """
        Initialize template configuration.

        Args:
            config: Configuration dictionary

        Raises:
            TemplateValidationError: Invalid configuration
        """
        pass

    @classmethod
    def from_file(cls, path: str) -> 'TemplateConfig':
        """
        Load configuration from file.

        Args:
            path: Path to config file

        Returns:
            Template configuration

        Raises:
            TemplateConfigError: Invalid configuration file
        """
        pass

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if valid, False otherwise

        Raises:
            TemplateValidationError: Validation errors
        """
        pass

    def get_variable(self, name: str, default: Any = None) -> Any:
        """
        Get template variable value.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            Variable value

        Raises:
            KeyError: Variable not found and no default
        """
        pass

    def to_dict(self) -> Dict:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        pass
```

### TemplateRenderer

Handles template rendering and variable substitution.

```python
class TemplateRenderer:
    def __init__(self, config: TemplateConfig, template: str):
        """
        Initialize template renderer.

        Args:
            config: Template configuration
            template: Template content
        """
        pass

    def render(self, context: Dict) -> str:
        """
        Render template with context.

        Args:
            context: Template context variables

        Returns:
            Rendered template

        Raises:
            TemplateVariableError: Missing or invalid variables
            TemplateSyntaxError: Invalid template syntax
        """
        pass

    def validate_syntax(self) -> bool:
        """
        Validate template syntax.

        Returns:
            True if valid, False otherwise

        Raises:
            TemplateSyntaxError: Invalid syntax
        """
        pass

    def get_required_variables(self) -> Set[str]:
        """
        Get required template variables.

        Returns:
            Set of required variable names
        """
        pass
```

### Template Exceptions

Custom exceptions for template-related errors.

```python
class TemplateError(Exception):
    """Base class for template exceptions."""
    pass

class TemplateNotFoundError(TemplateError):
    """Raised when template is not found."""
    pass

class TemplateConfigError(TemplateError):
    """Raised when template configuration is invalid."""
    pass

class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""
    pass

class TemplateVersionError(TemplateError):
    """Raised when template version is invalid."""
    pass

class TemplateVariableError(TemplateError):
    """Raised when template variable is invalid or missing."""
    pass

class TemplateSyntaxError(TemplateError):
    """Raised when template syntax is invalid."""
    pass
```

### Version

Manages template version information.

```python
class Version:
    def __init__(self, version_str: str):
        """
        Initialize version.

        Args:
            version_str: Version string (MAJOR.MINOR.PATCH)

        Raises:
            TemplateVersionError: Invalid version format
        """
        pass

    @property
    def major(self) -> int:
        """Get major version number."""
        pass

    @property
    def minor(self) -> int:
        """Get minor version number."""
        pass

    @property
    def patch(self) -> int:
        """Get patch version number."""
        pass

    def __str__(self) -> str:
        """Get version string."""
        pass

    def __eq__(self, other: 'Version') -> bool:
        """Compare versions for equality."""
        pass

    def __lt__(self, other: 'Version') -> bool:
        """Compare versions for ordering."""
        pass
``` 