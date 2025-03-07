# Schema System

The BenchPRO Schema System provides a robust framework for validating configurations using Pydantic models. It supports layered validation, extensibility, and comprehensive error reporting.

## Overview

The schema system consists of several components:

1. **Base Schema Classes**: Define common fields and behaviors
2. **Task-specific Schemas**: Define fields specific to different task types
3. **Global Configuration Schema**: Defines global settings
4. **Validation Layer**: Validates configurations against appropriate schemas

## Schema Architecture

### Base Task Schema

The `BaseTaskSchema` defines common fields for all task types:

```python
class BaseTaskSchema(BaseModel):
    """Base schema for task configurations."""
    
    task_type: str = Field(..., description="Type of task (application, benchmark)")
    name: str = Field(..., description="Name of the task")
    version: str = Field("1.0", description="Version of the task")
    description: Optional[str] = Field(None, description="Description of the task")
```

This base schema ensures all tasks have consistent basic fields.

### Task-Specific Schemas

The system includes two main task schemas:

1. **ApplicationSchema**: For application build tasks
2. **BenchmarkSchema**: For benchmark execution tasks

Both inherit from the `BaseTaskSchema` and add task-specific fields:

```python
class ApplicationSchema(BaseTaskSchema):
    """Schema for application configuration."""
    
    build: BuildConfig
    environment: EnvironmentConfig
    execution: Optional[ExecutionConfig]
    job: JobConfig
    workspace: WorkspaceConfig
    template: str
```

### Global Configuration Schema

The `GlobalConfigSchema` defines fields for global settings:

```python
class GlobalConfigSchema(BaseModel):
    """Schema for global configuration settings."""
    
    logging: Optional[LoggingConfig]
    paths: Optional[PathsConfig]
    workspace: Optional[GlobalWorkspaceConfig]
```

This schema allows validation of global settings separately from task-specific settings.

## Schema Features

### Extensibility

All schemas are configured with `extra="allow"` to permit additional fields:

```python
model_config = ConfigDict(extra="allow")
```

This allows users to define custom fields without breaking validation.

### Field Documentation

Fields include detailed descriptions for documentation generation:

```python
source: str = Field(..., description="Source file or directory for the application")
```

### Default Values

Fields can have sensible default values:

```python
threads: int = Field(1, description="Number of threads to use for building")
```

### Type Validation

The schema system validates types and provides helpful error messages:

```python
nodes: int = Field(1, description="Number of nodes to request")
```

### Nested Schemas

Schemas can be nested for complex configurations:

```python
build: BuildConfig = Field(..., description="Build configuration")
```

## Layered Validation

The validation process occurs in layers:

### 1. Global Validation

Global settings are validated against the `GlobalConfigSchema`:

```python
def validate_global(self, config: Dict[str, Any]) -> Dict[str, Any]:
    global_fields = {
        "logging": config.get("logging", {}),
        "paths": config.get("paths", {}),
        "workspace": {...}  # Global workspace fields
    }
    
    validated = GlobalConfigSchema(**global_fields)
    return validated.model_dump()
```

### 2. Task Validation

Task-specific settings are validated against the appropriate task schema:

```python
def validate_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
    config_copy = self._preprocess_config(config)
    task_type = config_copy["task_type"]
    schema_class = self.schema_map[task_type]
    
    validated = schema_class(**config_copy)
    return validated.model_dump()
```

### 3. Combined Validation

The `validate` method performs both validations and merges the results:

```python
def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
    validated_global = self.validate_global(config)
    validated_task = self.validate_task(config)
    
    result = {**validated_global, **validated_task}
    return result
```

## Legacy Field Handling

The system handles legacy fields through preprocessing:

```python
def _preprocess_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
    config_copy = copy.deepcopy(config)
    
    # Handle scheduler -> job conversion
    if "scheduler" in config_copy:
        if "job" not in config_copy:
            config_copy["job"] = {}
        config_copy["job"].update(config_copy.pop("scheduler"))
    
    # Remove fields that should not be part of task validation
    for field in ["system"]:
        if field in config_copy:
            config_copy.pop(field)
    
    return config_copy
```

## Error Handling

The validation system provides clear error messages:

```python
try:
    validated = schema_class(**config_copy)
    return validated.model_dump()
except ValidationError as e:
    error_messages = []
    for error in e.errors():
        loc = ".".join(str(l) for l in error["loc"])
        msg = error["msg"]
        error_messages.append(f"Task config error at {loc}: {msg}")
    
    formatted_error = "\n".join(error_messages)
    raise ValueError(f"Task configuration failed: {formatted_error}")
```

## Usage Examples

### Validating a Configuration

```python
from benchpro.config.validator import ConfigValidator

validator = ConfigValidator()

config = {
    "task_type": "application",
    "name": "hello_world",
    "build": {
        "source": "hello_world.c",
        "compiler": "gcc",
        "output": "hello_world"
    },
    "workspace": {
        "source_dir": "source"
    },
    "template": "hello_world.j2",
    "logging": {
        "level": "DEBUG"
    }
}

validated_config = validator.validate(config)
```

### Extending the Schema System

To add a new schema:

```python
from pydantic import BaseModel, Field, ConfigDict
from benchpro.config.schema.base import BaseTaskSchema

class CustomTaskSchema(BaseTaskSchema):
    """Schema for custom task configurations."""
    
    custom_field: str = Field(..., description="Custom field")
    
    model_config = ConfigDict(extra="allow")

# Register with the validator
validator.schema_map["custom"] = CustomTaskSchema
```

## Best Practices

1. **Use layered validation** for complex configurations
2. **Define clear schemas** with detailed field descriptions
3. **Set reasonable defaults** for optional fields
4. **Use nested models** for structured configurations
5. **Allow extensions** with `extra="allow"`
6. **Provide clear error messages** for validation failures

## See Also

- [Configuration Manager](config_manager.md): Using the configuration manager
- [Configuration Interfaces](interfaces.md): Interfaces for the configuration system 