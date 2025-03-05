"""
Task Factory for BenchPRO.

This module provides a factory for creating task instances.
"""

from typing import Optional

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.executor.task_base import Task
from benchpro.executor.application_task import Application
from benchpro.executor.benchmark_task import Benchmark
from benchpro.utils.logger import get_logger


class TaskFactory:
    """Factory for creating Task instances."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, 
                 template_engine: Optional[TemplateEngine] = None,
                 workspace_manager: Optional[WorkspaceManager] = None,
                 registry_manager: Optional[RegistryManager] = None):
        """
        Initialize the TaskFactory.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            template_engine: Optional TemplateEngine instance. If None, a new one is created.
            workspace_manager: Optional WorkspaceManager instance. If None, a new one is created.
            registry_manager: Optional RegistryManager instance. If None, a new one is created.
        """
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing TaskFactory")
        
        self.config_manager = config_manager or ConfigManager()
        self.template_engine = template_engine or TemplateEngine()
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.registry_manager = registry_manager or RegistryManager()
    
    def create_task(self, task_type: str) -> Task:
        """
        Create a Task instance of the specified type.
        
        Args:
            task_type: Type of task to create ("application" or "benchmark").
            
        Returns:
            A Task instance of the specified type.
            
        Raises:
            ValueError: If the task type is not recognized.
        """
        self.logger.debug(f"Creating task of type: {task_type}")
        
        if task_type.lower() == "application":
            self.logger.debug("Creating Application task")
            return Application(self.config_manager, self.template_engine, self.workspace_manager, self.registry_manager)
        elif task_type.lower() == "benchmark":
            self.logger.debug("Creating Benchmark task")
            return Benchmark(self.config_manager, self.template_engine, self.workspace_manager, self.registry_manager)
        else:
            error_msg = f"Unknown task type: {task_type}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) 