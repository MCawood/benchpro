"""
Composition-Based Task Classes for BenchPRO.

This module defines the composition-based Task classes for BenchPRO, using the component
interfaces to enable more flexible and testable implementation.
"""

import os
from typing import Dict, Any, Optional, Tuple, List

from benchpro.executor.components.interfaces import (
    ConfigComponent, ValidationComponent, ScriptGenerationComponent, ExecutionComponent,
    ConfigError, ValidationError, TemplateError, ExecutionError
)
from benchpro.utils.logger import get_logger


class Task:
    """
    Base class for all BenchPRO tasks, using component composition.
    
    This implementation uses composition rather than inheritance, accepting components
    that handle specific responsibilities as dependencies.
    """
    
    def __init__(self, 
                 config_component: ConfigComponent,
                 validation_component: ValidationComponent,
                 script_generation_component: ScriptGenerationComponent,
                 execution_component: ExecutionComponent):
        """
        Initialize the Task with its component dependencies.
        
        Args:
            config_component: Component for loading and managing configuration.
            validation_component: Component for validating configuration.
            script_generation_component: Component for generating scripts.
            execution_component: Component for executing scripts.
        """
        self.logger = get_logger(__name__)
        self.logger.info(f"Initializing {self.__class__.__name__} with component architecture")
        
        # Store component dependencies
        self.config_component = config_component
        self.validation_component = validation_component
        self.script_generation_component = script_generation_component
        self.execution_component = execution_component
        
        # Log component types for debugging
        self.logger.debug(f"{self.__class__.__name__} initialized with components:")
        self.logger.debug(f"  - ConfigComponent: {self.config_component.__class__.__name__}")
        self.logger.debug(f"  - ValidationComponent: {self.validation_component.__class__.__name__}")
        self.logger.debug(f"  - ScriptGenerationComponent: {self.script_generation_component.__class__.__name__}")
        self.logger.debug(f"  - ExecutionComponent: {self.execution_component.__class__.__name__}")
        
    def prepare(self, config_path: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prepare the task by loading and validating configuration.
        
        Args:
            config_path: Path to the configuration file.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            The merged and validated configuration.
            
        Raises:
            ConfigError: If the configuration cannot be loaded or merged.
            ValidationError: If the configuration validation fails.
        """
        self.logger.info(f"Preparing task with configuration: {config_path}")
        
        try:
            # Load configuration
            self.logger.debug("Loading configuration")
            config = self.config_component.load_config(config_path)
            
            # Merge with overrides if provided
            if cli_overrides:
                self.logger.debug("Merging with CLI overrides")
                config = self.config_component.merge_config(cli_overrides)
            
            # Validate configuration
            self.logger.debug("Validating configuration")
            is_valid, errors = self.validation_component.validate(config)
            
            if not is_valid:
                error_msg = f"Configuration validation failed: {', '.join(errors)}"
                self.logger.error(error_msg)
                raise ValidationError(error_msg)
            
            self.logger.info("Task preparation complete")
            return config
            
        except ConfigError as e:
            self.logger.error(f"Configuration error: {str(e)}")
            raise
        except ValidationError as e:
            self.logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during preparation: {str(e)}")
            raise
    
    def generate_script(self, template_path: str, output_path: str) -> str:
        """
        Generate a job script from a template.
        
        Args:
            template_path: Path to the template file.
            output_path: Path where the generated script should be saved.
            
        Returns:
            Path to the generated script.
            
        Raises:
            TemplateError: If the template cannot be loaded or rendered.
        """
        self.logger.info(f"Generating script from template: {template_path}")
        
        try:
            # Get the current configuration
            config = self.config_component.get_config()
            
            # Log workspace details if available
            if "workspace" in config:
                workspace = config.get("workspace", {})
                self.logger.debug(f"Using workspace directory: {workspace.get('workspace_dir', 'Not specified')}")
                self.logger.debug(f"Script will be generated at: {output_path}")
            else:
                self.logger.warning("No workspace configuration found in task config")
            
            # Prepare variables for the template
            variables = self.script_generation_component.prepare_variables(config)
            
            # Generate the script content
            self.logger.debug("Generating script content")
            script_content = self.script_generation_component.generate_script(template_path, variables)
            
            # Write script content to file
            self.logger.debug(f"Writing script to: {output_path}")
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(script_content)
            
            # Make the script executable
            os.chmod(output_path, 0o755)
            
            self.logger.info(f"Job script generated: {output_path}")
            return output_path
            
        except TemplateError as e:
            self.logger.error(f"Template error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during script generation: {str(e)}")
            raise TemplateError(f"Failed to generate script: {str(e)}")
    
    def submit_job(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Submit the job using the execution component.
        
        Args:
            script_path: Path to the job script.
            
        Returns:
            Tuple containing:
                - Success flag (True if successful, False otherwise)
                - Job ID (if submitted, None otherwise)
                
        Raises:
            ExecutionError: If the job submission fails.
        """
        self.logger.info(f"Submitting job: {script_path}")
        
        try:
            # Use the execution component to submit the job
            success, job_id = self.execution_component.execute(script_path)
            
            if success:
                self.logger.info(f"Job submitted successfully. Job ID: {job_id}")
            else:
                self.logger.error("Job submission failed")
                
            return success, job_id
            
        except ExecutionError as e:
            self.logger.error(f"Execution error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during job submission: {str(e)}")
            raise ExecutionError(f"Failed to submit job: {str(e)}")
    
    def get_job_status(self, job_id: str) -> str:
        """
        Get the status of a submitted job.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Status of the job as a string.
            
        Raises:
            StatusCheckError: If the status check fails.
        """
        self.logger.debug(f"Checking status of job: {job_id}")
        return self.execution_component.get_status(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a submitted job.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
            
        Raises:
            CancellationError: If the job cancellation fails.
        """
        self.logger.info(f"Cancelling job: {job_id}")
        return self.execution_component.cancel_job(job_id)


class Application(Task):
    """
    Application task for building applications, using component composition.
    """
    
    def __init__(self, 
                 config_component: ConfigComponent,
                 validation_component: ValidationComponent,
                 script_generation_component: ScriptGenerationComponent,
                 execution_component: ExecutionComponent,
                 registry_manager=None):  # Registry manager is kept for backward compatibility
        """
        Initialize the Application task with its component dependencies.
        
        Args:
            config_component: Component for loading and managing configuration.
            validation_component: Component for validating configuration.
            script_generation_component: Component for generating scripts.
            execution_component: Component for executing scripts.
            registry_manager: Optional registry manager for application registration.
        """
        super().__init__(config_component, validation_component, script_generation_component, execution_component)
        self.registry_manager = registry_manager
        if registry_manager:
            self.logger.debug(f"Application task initialized with RegistryManager: {self.registry_manager.__class__.__name__}")
    
    def register_application(self, binary_path: str) -> str:
        """
        Register the application with the registry after a successful build.
        
        Args:
            binary_path: Path to the built binary.
            
        Returns:
            The application ID if registration was successful, empty string otherwise.
        """
        if not self.registry_manager:
            self.logger.warning("Cannot register application: No registry manager available")
            return ""
            
        config = self.config_component.get_config()
        app_name = config.get("name", "unnamed_app")
        app_version = config.get("version", "1.0")
        
        # Extract build parameters if available
        build_params = config.get("build", {}).get("parameters", {})
        
        # Create application data dictionary for registration
        app_data = {
            "name": app_name,
            "version": app_version,
            "workspace_dir": os.path.dirname(os.path.dirname(binary_path)),
            "binary_path": binary_path,
            "build_parameters": build_params,
            "metadata": {
                "description": config.get("description", ""),
                "tags": config.get("tags", [])
            }
        }
        
        self.logger.info(f"Registering application {app_name} (version {app_version})")
        
        try:
            # Register the application
            app_id = self.registry_manager.register_application(app_data)
            
            if app_id:
                self.logger.info(f"Successfully registered application {app_name} with ID: {app_id}")
            else:
                self.logger.error(f"Failed to register application {app_name}")
                
            return app_id
        except Exception as e:
            self.logger.error(f"Error registering application: {str(e)}")
            return ""


class Benchmark(Task):
    """
    Benchmark task for running benchmarks, using component composition.
    """
    
    def __init__(self, 
                 config_component: ConfigComponent,
                 validation_component: ValidationComponent,
                 script_generation_component: ScriptGenerationComponent,
                 execution_component: ExecutionComponent,
                 registry_manager=None,  # Registry manager is kept for backward compatibility
                 result_extractor=None,  # Result extractor is kept for backward compatibility
                 result_capture=None):   # Result capture is kept for backward compatibility
        """
        Initialize the Benchmark task with its component dependencies.
        
        Args:
            config_component: Component for loading and managing configuration.
            validation_component: Component for validating configuration.
            script_generation_component: Component for generating scripts.
            execution_component: Component for executing scripts.
            registry_manager: Optional registry manager for benchmark registration.
            result_extractor: Optional result extractor for extracting benchmark results.
            result_capture: Optional result capture for capturing benchmark results.
        """
        super().__init__(config_component, validation_component, script_generation_component, execution_component)
        self.registry_manager = registry_manager
        self.result_extractor = result_extractor
        self.result_capture = result_capture
        
        if registry_manager:
            self.logger.debug(f"Benchmark task initialized with RegistryManager: {self.registry_manager.__class__.__name__}")
        if result_extractor:
            self.logger.debug(f"Benchmark task initialized with ResultExtractor: {self.result_extractor.__class__.__name__}")
        if result_capture:
            self.logger.debug(f"Benchmark task initialized with ResultCapture: {self.result_capture.__class__.__name__}") 