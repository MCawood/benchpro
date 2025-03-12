# Task Components

The BenchPRO task system uses a composition-based architecture with interchangeable components to improve flexibility, testability, and extensibility.

## Overview

The task component architecture replaces the inheritance-based approach previously used for tasks. Instead of having a rigid inheritance hierarchy, tasks are now composed of interchangeable components that handle specific responsibilities.

Key advantages of this approach include:
- **Flexibility**: Components can be swapped out independently of one another
- **Testability**: Components can be tested in isolation with mock dependencies
- **Extensibility**: New components can be added without modifying existing code
- **Reusability**: Components can be shared across different task types

## Component Interfaces

### ConfigComponent

The `ConfigComponent` interface defines functionality for loading, validating, and accessing task configuration.

```python
class ConfigComponent(ABC):
    """
    Interface for components that handle task configuration.
    """
    
    @abstractmethod
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            Loaded configuration as a dictionary.
        """
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Current configuration as a dictionary.
        """
        pass
    
    @abstractmethod
    def merge_config(self, override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge override configuration with the current configuration.
        
        Args:
            override_config: Configuration to merge with the current configuration.
            
        Returns:
            Merged configuration as a dictionary.
        """
        pass
```

Key responsibilities:
- Loading configuration from YAML files
- Providing access to configuration values
- Merging override configurations

### ValidationComponent

The `ValidationComponent` interface defines functionality for validating task configuration.

```python
class ValidationComponent(ABC):
    """
    Interface for components that validate task configuration.
    """
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate a configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            A tuple containing:
                - True if the configuration is valid, False otherwise.
                - List of validation error messages (if any).
        """
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        Get the list of required fields for this task type.
        
        Returns:
            List of required field names.
        """
        pass
```

Key responsibilities:
- Validating configuration structure
- Ensuring required fields are present
- Validating field values against constraints

### ScriptGenerationComponent 

The `ScriptGenerationComponent` interface defines functionality for generating execution scripts.

```python
class ScriptGenerationComponent(ABC):
    """
    Interface for components that generate execution scripts.
    """
    
    @abstractmethod
    def generate_script(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Generate a script from a template.
        
        Args:
            template_path: Path to the template file.
            variables: Variables to use when rendering the template.
            
        Returns:
            Generated script content as a string.
        """
        pass
    
    @abstractmethod
    def prepare_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare variables for template rendering.
        
        Args:
            config: Task configuration.
            
        Returns:
            Dictionary of variables for template rendering.
        """
        pass
```

Key responsibilities:
- Rendering templates with configuration variables
- Generating appropriate script headers (e.g., Slurm directives)
- Preparing variables for template rendering

### ExecutionComponent

The `ExecutionComponent` interface defines functionality for executing scripts.

```python
class ExecutionComponent(ABC):
    """
    Interface for components that execute scripts.
    """
    
    @abstractmethod
    def execute(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Execute a script.
        
        Args:
            script_path: Path to the script to execute.
            
        Returns:
            A tuple containing:
                - True if the script was successfully submitted, False otherwise.
                - Job ID or process ID (if submitted, None otherwise).
        """
        pass
    
    @abstractmethod
    def get_status(self, job_id: str) -> str:
        """
        Get the status of a job.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Status of the job as a string (e.g., "RUNNING", "COMPLETED", "FAILED").
        """
        pass
    
    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
        """
        pass
```

Key responsibilities:
- Executing scripts using appropriate mechanisms (local or scheduler)
- Tracking and reporting job status
- Cancelling running jobs when requested

## Component Exceptions

The component system defines a hierarchy of exceptions for handling errors:

```python
class ComponentError(Exception):
    """Base class for all component-related exceptions."""
    pass

class ConfigError(ComponentError):
    """Exception raised when a configuration error occurs."""
    pass

class ValidationError(ComponentError):
    """Exception raised when a validation error occurs."""
    pass

class TemplateError(ComponentError):
    """Exception raised when a template error occurs."""
    pass

class ExecutionError(ComponentError):
    """Exception raised when an execution error occurs."""
    pass

class StatusCheckError(ComponentError):
    """Exception raised when a status check error occurs."""
    pass

class CancellationError(ComponentError):
    """Exception raised when a job cancellation error occurs."""
    pass
```

## Usage Guidelines

When implementing and using components:

1. **Keep components focused**: Each component should have a single responsibility.
2. **Make components stateless when possible**: This improves testability and reusability.
3. **Use composition over inheritance**: Components should delegate to other components rather than inheriting from them.
4. **Implement robust error handling**: Components should raise appropriate exceptions when errors occur.
5. **Document component behavior**: Clearly document the expected behavior and contract of each component.

## Example Usage

Components are intended to be instantiated by a factory and injected into Task instances. They are not typically created or used directly by client code.

Example task implementation using components:

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
        
    def run(self):
        # Get and validate configuration
        config = self.config_component.get_config()
        is_valid, errors = self.validation_component.validate(config)
        if not is_valid:
            raise ValidationError(f"Invalid configuration: {errors}")
        
        # Generate script
        variables = self.script_generation_component.prepare_variables(config)
        script_content = self.script_generation_component.generate_script(
            config["template"], variables
        )
        
        # Write script to file and execute
        script_path = self._write_script_to_file(script_content)
        success, job_id = self.execution_component.execute(script_path)
        
        return job_id
```

## Testing Components

Components should be tested in isolation using mock dependencies. This allows for thorough testing of component behavior without requiring complex setup or external resources.

Example test for a script generation component:

```python
def test_slurm_script_generator():
    # Create mock template engine
    mock_template_engine = MagicMock()
    mock_template_engine.render.return_value = "echo 'Hello, World!'"
    
    # Create the component with the mock
    generator = SlurmScriptGenerator(template_engine=mock_template_engine)
    
    # Test
    variables = {"job": {"name": "test_job", "nodes": 2}}
    result = generator.generate_script("dummy_path", variables)
    
    # Verify Slurm directives are added
    assert "#SBATCH -J test_job" in result
    assert "#SBATCH -N 2" in result
    
    # Verify template content is included
    assert "echo 'Hello, World!'" in result
``` 