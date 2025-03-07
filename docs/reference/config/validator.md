# Configuration Validator

The `ConfigValidator` is responsible for validating configurations against schemas, providing schema information, and generating example configurations.

## Overview

The `ConfigValidator` implements the `ConfigValidatorInterface` and provides:

1. **Layered Validation**: Validates global and task-specific settings separately
2. **Schema Management**: Maintains a registry of available schemas
3. **Error Reporting**: Provides detailed error messages for validation failures
4. **Example Generation**: Generates example configurations

## Key Methods

### validate

```python
def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a complete configuration dictionary against appropriate schemas.
    
    This method:
    1. Makes a copy of the configuration to avoid modifying the original
    2. Validates global settings
    3. Validates task-specific settings
    4. Merges the validated configurations
    
    Args:
        config: Configuration dictionary to validate.
        
    Returns:
        Validated configuration dictionary.
        
    Raises:
        ValueError: If the configuration is invalid or the task type is unknown.
    """
```

This method is the main entry point for validating configurations. It performs both global and task-specific validation and merges the results.

### validate_global

```python
def validate_global(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the global configuration settings.
    
    Args:
        config: Configuration dictionary to validate.
        
    Returns:
        Validated global configuration dictionary.
        
    Raises:
        ValueError: If the global configuration is invalid.
    """
```

This method validates global settings against the `GlobalConfigSchema`.

### validate_task

```python
def validate_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate task-specific configuration settings.
    
    This method:
    1. Preprocesses the configuration to handle legacy fields
    2. Determines the task type
    3. Validates against the appropriate task schema
    
    Args:
        config: Configuration dictionary to validate.
        
    Returns:
        Validated task configuration dictionary.
        
    Raises:
        ValueError: If the task configuration is invalid or the task type is unknown.
    """
```

This method validates task-specific settings against the appropriate task schema.

### get_schema

```python
def get_schema(self, task_type: str) -> Dict[str, Any]:
    """
    Get the schema for a task type.
    
    Args:
        task_type: Type of task (application or benchmark).
        
    Returns:
        Schema dictionary.
        
    Raises:
        ValueError: If the task type is unknown.
    """
```

This method returns the schema for a given task type.

### get_schema_json

```python
def get_schema_json(self, task_type: str) -> str:
    """
    Get the schema for a task type as JSON.
    
    Args:
        task_type: Type of task (application or benchmark).
        
    Returns:
        Schema as JSON string.
        
    Raises:
        ValueError: If the task type is unknown.
    """
```

This method returns the schema for a given task type as a JSON string.

### get_example_config

```python
def get_example_config(self, task_type: str) -> Dict[str, Any]:
    """
    Get an example configuration for the given task type.
    
    Args:
        task_type: Type of task (application or benchmark)
        
    Returns:
        Example configuration
        
    Raises:
        ValueError: If the task type is unknown.
    """
```

This method returns an example configuration for a given task type.

## Private Methods

### _preprocess_config

```python
def _preprocess_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocess the configuration to handle legacy fields and cleanup.
    
    Args:
        config: Configuration dictionary to preprocess.
        
    Returns:
        Preprocessed configuration dictionary.
    """
```

This method preprocesses configurations to handle legacy fields and clean up irrelevant fields.

## Usage Examples

### Basic Validation

```python
from benchpro.config.validator import ConfigValidator

validator = ConfigValidator()

# Configuration to validate
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
    "template": "hello_world.j2"
}

# Validate the configuration
try:
    validated_config = validator.validate(config)
    print("Configuration is valid!")
except ValueError as e:
    print(f"Configuration is invalid: {e}")
```

### Getting Schema Information

```python
from benchpro.config.validator import ConfigValidator
import json

validator = ConfigValidator()

# Get schema for application task type
schema = validator.get_schema("application")

# Print schema as pretty JSON
print(json.dumps(schema, indent=2))
```

### Generating Example Configuration

```python
from benchpro.config.validator import ConfigValidator
import yaml

validator = ConfigValidator()

# Get example configuration for benchmark task type
example = validator.get_example_config("benchmark")

# Print example as YAML
print(yaml.dump(example, default_flow_style=False))
```

## Error Handling

The `ConfigValidator` provides detailed error messages for validation failures:

```python
from benchpro.config.validator import ConfigValidator

validator = ConfigValidator()

# Invalid configuration (missing required fields)
config = {
    "task_type": "application",
    "name": "hello_world"
    # Missing build, workspace, template
}

# Validate the configuration
try:
    validated_config = validator.validate(config)
    print("Configuration is valid!")
except ValueError as e:
    print(f"Configuration is invalid: {e}")
    # Will print detailed error messages for missing fields
```

## Best Practices

1. **Use layered validation** for complex configurations
2. **Handle legacy fields** through preprocessing
3. **Provide detailed error messages** for validation failures
4. **Generate example configurations** for documentation
5. **Use schema generation** for API documentation

## See Also

- [Schema System](schema.md): Schema-based validation for configuration files
- [Configuration Manager](config_manager.md): Using the configuration manager 