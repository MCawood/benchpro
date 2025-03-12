"""
Task Factory for BenchPRO using the composition-based architecture.

This module provides a factory for creating tasks with appropriate components.
"""

import os
from typing import Dict, Any, Optional, List, Type

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.utils.user_dir import get_user_dir_manager

from benchpro.executor.components.configuration import (
    ApplicationConfigComponent, BenchmarkConfigComponent
)
from benchpro.executor.components.validation import (
    ApplicationValidationComponent, BenchmarkValidationComponent
)
from benchpro.executor.components.script_generation import (
    LocalScriptGenerator, SlurmScriptGenerator
)
from benchpro.executor.components.execution import (
    LocalExecutionComponent, SlurmExecutionComponent
)
from benchpro.executor.task import Task, Application, Benchmark

from benchpro.utils.logger import get_logger


class TaskFactory:
    """
    Factory for creating task instances using the composition-based architecture.
    
    This factory creates tasks with appropriate components based on the task type
    and execution type.
    """
    
    def __init__(self):
        """Initialize the TaskFactory."""
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing TaskFactory")
        
    def create_task(self, task_type: str, execution_type: Optional[str] = None, 
                   config: Optional[Dict[str, Any]] = None) -> Task:
        """
        Create a task instance with appropriate components.
        
        Args:
            task_type: Type of task to create ("application" or "benchmark").
            execution_type: Type of execution to use ("local" or "slurm").
                           If None, defaults to "local".
            config: Optional configuration dictionary to use for component creation.
                   
        Returns:
            A Task instance of the appropriate type with configured components.
            
        Raises:
            ValueError: If an invalid task_type or execution_type is provided.
        """
        self.logger.debug(f"Creating task of type: {task_type} with execution type: {execution_type or 'default'}")
        
        # Default to local execution if not specified
        if not execution_type:
            execution_type = "local"
            
        # Validate task type
        if task_type not in ["application", "benchmark"]:
            raise ValueError(f"Invalid task type: {task_type}. Must be 'application' or 'benchmark'.")
            
        # Validate execution type
        if execution_type not in ["local", "slurm"]:
            raise ValueError(f"Invalid execution type: {execution_type}. Must be 'local' or 'slurm'.")
        
        # Create components based on task type and execution type
        config_component = self._create_config_component(task_type, config)
        validation_component = self._create_validation_component(task_type)
        script_gen_component = self._create_script_generation_component(execution_type)
        execution_component = self._create_execution_component(execution_type)
        
        # Create and return the task instance
        if task_type == "application":
            return Application(
                config_component=config_component,
                validation_component=validation_component,
                script_generation_component=script_gen_component,
                execution_component=execution_component
            )
        else:  # task_type == "benchmark"
            return Benchmark(
                config_component=config_component,
                validation_component=validation_component,
                script_generation_component=script_gen_component,
                execution_component=execution_component
            )
    
    def _create_config_component(self, task_type: str, config: Optional[Dict[str, Any]] = None):
        """
        Create the appropriate config component based on task type.
        
        Args:
            task_type: Type of task ("application" or "benchmark").
            config: Optional configuration dictionary with additional options.
            
        Returns:
            A config component instance appropriate for the task type.
            
        Raises:
            ValueError: If an unknown task type is provided.
        """
        if task_type.lower() == "application":
            # Log that we're creating an application config component
            self.logger.debug(f"Creating ApplicationConfigComponent with task_type={task_type.lower()}")
            
            # Create the component with workspace details from config if available
            component = ApplicationConfigComponent(
                config_manager=ConfigManager(user_dir_manager=get_user_dir_manager()),
                user_dir_manager=get_user_dir_manager(),
                task_type=task_type.lower()  # Pass task_type explicitly
            )
            
            # If config is provided and has workspace details, set it directly
            if config and 'workspace' in config:
                self.logger.debug(f"Setting workspace configuration from provided config")
                component.set_config(config)
                
            return component
        elif task_type.lower() == "benchmark":
            # Log that we're creating a benchmark config component
            self.logger.debug(f"Creating BenchmarkConfigComponent with task_type={task_type.lower()}")
            
            # Create the component with workspace details from config if available
            component = BenchmarkConfigComponent(
                config_manager=ConfigManager(user_dir_manager=get_user_dir_manager()),
                user_dir_manager=get_user_dir_manager(),
                task_type=task_type.lower()  # Pass task_type explicitly
            )
            
            # If config is provided and has workspace details, set it directly
            if config and 'workspace' in config:
                self.logger.debug(f"Setting workspace configuration from provided config")
                component.set_config(config)
                
            return component
        else:
            raise ValueError(f"Unknown task type for config component: {task_type}")
    
    def _create_validation_component(self, task_type: str):
        """Create the appropriate validation component based on task type."""
        if task_type.lower() == "application":
            return ApplicationValidationComponent()
        elif task_type.lower() == "benchmark":
            return BenchmarkValidationComponent()
        else:
            raise ValueError(f"Unknown task type for validation component: {task_type}")
    
    def _create_script_generation_component(self, execution_type: str):
        """Create the appropriate script generation component based on execution type."""
        if execution_type.lower() == "local":
            return LocalScriptGenerator(template_engine=TemplateEngine(user_dir_manager=get_user_dir_manager()))
        elif execution_type.lower() == "slurm":
            return SlurmScriptGenerator(template_engine=TemplateEngine(user_dir_manager=get_user_dir_manager()))
        else:
            raise ValueError(f"Unknown execution type for script generation component: {execution_type}")
    
    def _create_execution_component(self, execution_type: str):
        """Create the appropriate execution component based on execution type."""
        if execution_type.lower() == "local":
            return LocalExecutionComponent()
        elif execution_type.lower() == "slurm":
            return SlurmExecutionComponent()
        else:
            raise ValueError(f"Unknown execution type for execution component: {execution_type}") 