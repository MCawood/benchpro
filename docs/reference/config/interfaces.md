# Configuration Interfaces

The BenchPRO configuration system uses a set of interfaces to provide a clean architecture and facilitate dependency injection and testing.

## Overview

The configuration system defines several interfaces:

1. **ConfigLoaderInterface**: For loading configuration from files
2. **ConfigMergerInterface**: For merging configurations with proper precedence
3. **VariableResolverInterface**: For resolving template variables in configurations
4. **ConfigValidatorInterface**: For validating configurations against schemas

Each interface defines a contract that implementation classes must follow.

## ConfigLoaderInterface

```python
@runtime_checkable
class ConfigLoaderInterface(Protocol):
    """
    Interface for loading configuration from different sources.
    
    Responsibilities:
    - Load configuration from files
    - Handle different file formats
    - Handle file system operations
    """
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from a file."""
    
    def load_default_config(self) -> Dict[str, Any]:
        """Load the default configuration."""
    
    def load_system_config(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        """Load the system-specific configuration."""
    
    def load_profile_config(self, profile_name: str, task_type: Optional[str] = None) -> Dict[str, Any]:
        """Load a profile configuration."""
```

## ConfigMergerInterface

```python
@runtime_checkable
class ConfigMergerInterface(Protocol):
    """
    Interface for merging configurations with proper precedence.
    
    Responsibilities:
    - Merge configurations from different sources
    - Handle precedence rules
    - Handle deep merging of nested dictionaries
    """
    
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configurations."""
    
    def merge_all(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple configurations."""
```

## VariableResolverInterface

```python
@runtime_checkable
class VariableResolverInterface(Protocol):
    """
    Interface for substituting variables in configuration values.
    
    Responsibilities:
    - Substitute variables in configuration values
    - Handle environment variables
    - Handle recursive variable references
    """
    
    def resolve(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute variables in configuration values."""
```

## ConfigValidatorInterface

```python
@runtime_checkable
class ConfigValidatorInterface(Protocol):
    """
    Interface for validating configuration against schemas.
    
    Responsibilities:
    - Validate configuration against schemas
    - Provide schema information
    - Generate example configurations
    """
    
    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete configuration dictionary against schemas."""
    
    def validate_global(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the global configuration settings."""
    
    def validate_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task-specific configuration settings."""
    
    def get_schema(self, task_type: str) -> Dict[str, Any]:
        """Get the schema for a task type."""
    
    def get_schema_json(self, task_type: str) -> str:
        """Get the schema for a task type as JSON."""
    
    def generate_example(self, task_type: str) -> Dict[str, Any]:
        """Generate an example configuration for a task type."""
```

## Using Interfaces for Dependency Injection

The interfaces enable dependency injection, allowing for easy testing and flexible implementations:

```python
class ConfigManager:
    def __init__(self, 
                 config_loader: Optional[ConfigLoaderInterface] = None,
                 config_merger: Optional[ConfigMergerInterface] = None,
                 variable_resolver: Optional[VariableResolverInterface] = None,
                 config_validator: Optional[ConfigValidatorInterface] = None):
        # Use provided components or create defaults
        self.config_loader = config_loader or YamlConfigLoader()
        self.config_merger = config_merger or HierarchicalConfigMerger()
        self.variable_resolver = variable_resolver or TemplateVariableResolver()
        self.config_validator = config_validator or ConfigValidator()
```

## Testing with Interfaces

Interfaces make it easy to create test doubles:

```python
class MockConfigLoader(ConfigLoaderInterface):
    def load_file(self, file_path: str) -> Dict[str, Any]:
        return {"mocked": True}
    
    def load_default_config(self) -> Dict[str, Any]:
        return {"default": True}
    
    def load_system_config(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        return {"system": system_name or "default"}
    
    def load_profile_config(self, profile_name: str, task_type: Optional[str] = None) -> Dict[str, Any]:
        return {"profile": profile_name, "task_type": task_type or "application"}

# Use the mock in tests
config_manager = ConfigManager(config_loader=MockConfigLoader())
```

## Creating Custom Implementations

You can create custom implementations of these interfaces to extend the system:

```python
class JsonConfigLoader(ConfigLoaderInterface):
    """Configuration loader for JSON files."""
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r") as f:
            return json.load(f)
    
    # ... implement other methods

# Use the custom implementation
config_manager = ConfigManager(config_loader=JsonConfigLoader())
```

## Best Practices

1. **Use interfaces for abstraction**: Define clear interfaces for each component
2. **Use dependency injection**: Pass dependencies explicitly rather than creating them
3. **Design for testability**: Make testing easy with interfaces
4. **Document interfaces clearly**: Each interface should have a clear contract

## See Also

- [Schema System](schema.md): Schema-based validation for configuration files
- [Configuration Validator](validator.md): Validating configurations 