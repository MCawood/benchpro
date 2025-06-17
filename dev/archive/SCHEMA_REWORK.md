# Schema Rework Plan for BenchPRO Configuration System

## 1. Current System Analysis

### 1.1 Purpose of Configuration Files

- **default.yaml**: Provides system-wide default configuration values that apply to all tasks.
  - Contains both global settings (logging, paths) and task-related defaults (job, execution).
  - Used as the base layer for all configurations.

- **system/[name].yaml**: Provides system-specific configurations for different computing environments.
  - Overrides default.yaml for system-specific settings.
  - Used as the second layer of configuration.

- **[profile].yaml**: User-defined task configurations (application or benchmark).
  - Contains task-specific settings that override defaults.
  - Used as the third layer of configuration.

- **CLI Overrides**: Command-line arguments that provide the highest precedence overrides.
  - Allow for quick modifications without changing configuration files.

### 1.2 Purpose of Schema Validation

- **Schemas (application.py, benchmark.py)**: Define the structure and constraints for valid configurations.
  - Ensure required fields are present.
  - Validate data types and ranges.
  - Provide documentation through field descriptions.
  - Define default values when not specified.

- **Validation Process**: The ConfigValidator validates merged configurations against the appropriate schema.
  - Ensures the final configuration meets all requirements.
  - Catches configuration errors before task execution.
  - Converts the validated configuration to a strongly-typed model.

### 1.3 Current Issues

1. **Schema-Configuration Mismatch**: Fields in default/system configurations (like logging, paths, global workspace settings) aren't defined in task schemas.

2. **Lack of Layered Validation**: The entire merged configuration is validated against a task-specific schema, rather than validating each layer appropriately.

3. **Schema Strictness**: Task schemas use `extra = "forbid"` which rejects any field not explicitly defined, limiting extensibility.

4. **Inflexible Field Handling**: Fields like "scheduler" that should be moved to "job" cause validation failures.

5. **No Global Schema**: There's no schema for global settings, making it difficult to validate non-task-specific configurations.

6. **Validation Happens Too Late**: Validation occurs after all merging and resolution, making it difficult to provide helpful error messages.

## 2. Design Principles for the New System

1. **Layered Configuration with Layered Validation**:
   - Each configuration layer should be validated against its appropriate schema.
   - Global settings should be validated separately from task-specific settings.

2. **Flexible Yet Strict**:
   - Validate critical fields strictly while allowing extension.
   - Support defining additional fields without breaking validation.

3. **Backward Compatibility**:
   - Maintain support for existing configuration files.
   - Handle legacy field names gracefully.

4. **Clear Error Messages**:
   - Provide clear information about validation failures.
   - Include context about which layer and field caused the error.

5. **Extensibility**:
   - Support extensible schemas for plugins or user-defined components.
   - Allow for future schema evolution without breaking existing configurations.

## 3. Implementation Plan

### 3.1 Create Global Configuration Schema

Create a `GlobalConfigSchema` that defines all global settings:

```python
class LoggingConfig(BaseModel):
    level: str = Field("INFO", description="Logging level")
    file: str = Field("benchpro.log", description="Log file name")
    
    class Config:
        extra = "allow"

class PathsConfig(BaseModel):
    modules: Optional[str] = Field(None, description="Path to modules directory")
    scratch: Optional[str] = Field(None, description="Path to scratch directory")
    
    class Config:
        extra = "allow"

class GlobalWorkspaceConfig(BaseModel):
    base_input_dir: str = Field("examples/input", description="Base input directory")
    base_output_dir: str = Field("examples/output", description="Base output directory")
    keep_source_files: bool = Field(True, description="Whether to keep source files")
    keep_build_files: bool = Field(True, description="Whether to keep build files")
    keep_logs: bool = Field(True, description="Whether to keep log files")
    
    class Config:
        extra = "allow"

class GlobalConfigSchema(BaseModel):
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    paths: PathsConfig = Field(default_factory=PathsConfig, description="Path configuration")
    workspace: GlobalWorkspaceConfig = Field(default_factory=GlobalWorkspaceConfig, description="Global workspace configuration")
    
    class Config:
        extra = "allow"
```

### 3.2 Update Task Schemas

Update the task schemas to focus only on task-specific fields and allow for extension:

1. Move common fields to a `BaseTaskSchema`:

```python
class BaseTaskSchema(BaseModel):
    task_type: str = Field(..., description="Type of task")
    name: str = Field(..., description="Name of the task")
    version: str = Field("1.0", description="Version of the task")
    description: Optional[str] = Field(None, description="Description of the task")
    
    class Config:
        extra = "allow"
```

2. Update ApplicationSchema and BenchmarkSchema to inherit from BaseTaskSchema and focus on task-specific fields.

3. Set `extra = "allow"` for all schema configs to permit additional fields.

### 3.3 Implement Layered Validation

Modify `ConfigValidator` to support layered validation:

```python
class ConfigValidator(ConfigValidatorInterface):
    def __init__(self):
        self.logger = get_logger(__name__)
        self.schema_map = {
            "application": ApplicationSchema,
            "benchmark": BenchmarkSchema,
            "global": GlobalConfigSchema
        }
    
    def validate_global(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate global configuration settings."""
        # Extract global fields
        global_fields = {
            "logging": config.get("logging", {}),
            "paths": config.get("paths", {}),
            "workspace": {
                "base_input_dir": config.get("workspace", {}).get("base_input_dir", "examples/input"),
                "base_output_dir": config.get("workspace", {}).get("base_output_dir", "examples/output"),
                "keep_source_files": config.get("workspace", {}).get("keep_source_files", True),
                "keep_build_files": config.get("workspace", {}).get("keep_build_files", True),
                "keep_logs": config.get("workspace", {}).get("keep_logs", True)
            }
        }
        
        # Validate global fields
        try:
            validated = GlobalConfigSchema(**global_fields)
            return validated.model_dump()
        except ValidationError as e:
            self.logger.error(f"Global configuration validation failed: {e}")
            raise ValueError(f"Global configuration validation failed: {e}")
    
    def validate_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task-specific configuration."""
        # Handle the legacy field conversions
        config_copy = self._preprocess_config(config)
        
        # Extract task-specific fields
        task_type = config_copy.get("task_type")
        if not task_type:
            raise ValueError("Configuration missing 'task_type' field")
        
        # Get the appropriate schema
        if task_type not in self.schema_map:
            raise ValueError(f"Unknown task type: {task_type}")
        
        schema_class = self.schema_map[task_type]
        
        # Validate task-specific fields
        try:
            validated = schema_class(**config_copy)
            return validated.model_dump()
        except ValidationError as e:
            self.logger.error(f"Task configuration validation failed: {e}")
            raise ValueError(f"Task configuration validation failed: {e}")
    
    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete configuration."""
        # Make a copy to avoid modifying the original
        config_copy = copy.deepcopy(config)
        
        # Validate global configuration
        validated_global = self.validate_global(config_copy)
        
        # Validate task-specific configuration
        validated_task = self.validate_task(config_copy)
        
        # Merge validated configurations
        result = {**validated_global, **validated_task}
        
        return result
    
    def _preprocess_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess the configuration to handle legacy fields."""
        config_copy = copy.deepcopy(config)
        
        # Handle scheduler -> job conversion
        if "scheduler" in config_copy:
            if "job" not in config_copy:
                config_copy["job"] = {}
            config_copy["job"].update(config_copy.pop("scheduler"))
        
        # Remove system field if it exists
        if "system" in config_copy:
            config_copy.pop("system")
        
        return config_copy
```

### 3.4 Update ConfigManager

Modify `ConfigManager` to use the new layered validation approach:

```python
def get_config(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get a complete, validated configuration for a profile.
    
    Args:
        profile_name: Name of the profile.
        cli_overrides: Optional dictionary of CLI parameter overrides.
        
    Returns:
        Complete, validated configuration.
        
    Raises:
        FileNotFoundError: If the profile doesn't exist.
        ValueError: If the configuration is invalid.
    """
    # Merge configurations
    merged_config = self.merge_configs(profile_name, cli_overrides)
    
    # Validate the configuration
    validated_config = self.config_validator.validate(merged_config)
    
    return validated_config
```

### 3.5 Improve Error Handling

Enhance error messages to clearly indicate which part of the configuration is invalid:

```python
def validate_global(self, config: Dict[str, Any]) -> Dict[str, Any]:
    # ...
    try:
        validated = GlobalConfigSchema(**global_fields)
        return validated.model_dump()
    except ValidationError as e:
        # Format error message with context
        error_messages = []
        for error in e.errors():
            loc = ".".join(str(l) for l in error["loc"])
            msg = error["msg"]
            error_messages.append(f"Global config error at {loc}: {msg}")
        
        formatted_error = "\n".join(error_messages)
        self.logger.error(f"Global configuration validation failed:\n{formatted_error}")
        raise ValueError(f"Global configuration validation failed:\n{formatted_error}")
```

### 3.6 Support for Schema Extensions

Add support for custom schema extensions:

```python
def register_schema(self, task_type: str, schema_class: Type[BaseModel]) -> None:
    """Register a new schema for a task type."""
    self.schema_map[task_type] = schema_class
    self.logger.info(f"Registered schema for task type: {task_type}")
```

### 3.7 Schema Documentation

Add tools to generate schema documentation from code:

```python
def generate_schema_documentation(self) -> Dict[str, Any]:
    """Generate documentation for all registered schemas."""
    docs = {}
    for task_type, schema_class in self.schema_map.items():
        docs[task_type] = {
            "schema": schema_class.schema(),
            "example": self.generate_example(task_type)
        }
    return docs
```

## 4. Testing Plan

### 4.1 Unit Tests

1. Test validation of global configuration fields
2. Test validation of task-specific fields
3. Test handling of legacy fields (scheduler -> job)
4. Test error messages for various validation failures
5. Test schema extensions

### 4.2 Integration Tests

1. Test validating complete configurations from files
2. Test CLI parameter overrides
3. Test handling all combinations of configuration layers

### 4.3 End-to-End Tests

1. Test actual execution with various configuration scenarios
2. Test backward compatibility with existing configuration files

## 5. Implementation Phases

### Phase 1: Core Schema Structure (Week 1)
- Create GlobalConfigSchema
- Update task schemas to allow extension
- Implement basic layered validation

### Phase 2: Validation Enhancements (Week 2)
- Implement preprocessing for legacy fields
- Improve error messages
- Add schema extension support

### Phase 3: Integration and Testing (Week 3)
- Update ConfigManager to use new validation
- Add comprehensive tests
- Create documentation

## 6. Migration Guide

### 6.1 For Users

- No changes needed for existing configuration files
- New global settings can now be used in any configuration layer

### 6.2 For Developers

- Use the new layered validation in custom components
- Register custom schemas for extensions
- Follow the new error handling pattern

## 7. Future Considerations

1. **Schema Versioning**: Add support for schema versions to allow for evolving schemas
2. **JSON Schema Export**: Export schemas as JSON Schema for external validation
3. **UI Integration**: Use schemas to generate configuration UIs
4. **Configuration Profiles**: Support named configuration profiles for different environments 