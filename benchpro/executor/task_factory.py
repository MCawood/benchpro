from typing import Dict, Any
from benchpro.config.config_manager import ConfigManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.executor.components.interfaces import (
    ConfigComponent, ValidationComponent, ExecutionComponent
)
from benchpro.executor.components.configuration import BaseConfigComponent
from benchpro.executor.components.validation import (
    ApplicationValidationComponent, BenchmarkValidationComponent
)
from benchpro.executor.components.execution import (
    LocalExecutionComponent, SlurmExecutionComponent
)
from benchpro.templates.script_generators import (
    LocalScriptGenerator, SlurmScriptGenerator, ScriptGenerationComponent
)
from benchpro.executor.task import Task, Application, Benchmark
from benchpro.utils.logger import get_logger

logger = get_logger(__name__)

class TaskFactory:
    """
    Factory for creating task instances with appropriate components.
    This factory uses dependency injection to assemble tasks.
    """

    def __init__(self, config_manager: ConfigManager, registry_manager: RegistryManager):
        """
        Initialize the TaskFactory.
        Args:
            config_manager: The configuration manager instance.
            registry_manager: The registry manager instance.
        """
        self.logger = get_logger(__name__)
        self.logger.info("Initializing TaskFactory with injected dependencies.")
        self.config_manager = config_manager
        self.registry_manager = registry_manager

    def create_task(self, config: Dict[str, Any]) -> Task:
        """
        Create a Task instance based on the provided configuration.
        Args:
            config: The merged configuration for the task.
        Returns:
            A fully-formed Task instance.
        """
        task_type = config.get("task_type")
        if not task_type:
            raise ValueError("Configuration must include a 'task_type'.")

        # Use execution.type as the canonical source for execution type
        # Fall back to "local" if not specified
        execution_type = config.get("execution", {}).get("type", "local")
        
        self.logger.info(f"Creating '{task_type}' task with execution type: '{execution_type}'")

        # Create components, using the injected managers
        config_component = self._create_config_component(config)
        validation_component = self._create_validation_component(task_type)
        script_generation_component = self._create_script_generation_component(execution_type)
        execution_component = self._create_execution_component(execution_type)

        # Assemble the task with its components, including registry manager
        if task_type.lower() == "application":
            task = Application(
                config_component=config_component,
                validation_component=validation_component,
                script_generation_component=script_generation_component,
                execution_component=execution_component,
                registry_manager=self.registry_manager
            )
        elif task_type.lower() == "benchmark":
            task = Benchmark(
                config_component=config_component,
                validation_component=validation_component,
                script_generation_component=script_generation_component,
                execution_component=execution_component,
                registry_manager=self.registry_manager
            )
        else:
            raise ValueError(f"Unsupported task type: {task_type}")

        self.logger.info(f"'{task_type}' task created successfully.")
        return task

    def _create_config_component(self, config: Dict[str, Any]) -> ConfigComponent:
        """Creates a ConfigComponent that uses the injected ConfigManager."""
        # Use the BaseConfigComponent which accepts config_manager parameter
        component = BaseConfigComponent(config_manager=self.config_manager)
        component.set_config(config)
        return component

    def _create_validation_component(self, task_type: str) -> ValidationComponent:
        """Create a ValidationComponent for the specified task type."""
        if task_type.lower() == "application":
            return ApplicationValidationComponent()
        elif task_type.lower() == "benchmark":
            return BenchmarkValidationComponent()
        raise ValueError(f"No validation component for task type: {task_type}")

    def _create_script_generation_component(self, execution_type: str) -> ScriptGenerationComponent:
        """Create a ScriptGenerationComponent for the specified execution type."""
        if execution_type.lower() == "local":
            script_generation_component = LocalScriptGenerator()
        elif execution_type.lower() == "sched":
            script_generation_component = SlurmScriptGenerator()
        else:
            logger.warning(f"Unknown execution type '{execution_type}', defaulting to local")
            script_generation_component = LocalScriptGenerator()
        
        return script_generation_component

    def _create_execution_component(self, execution_type: str) -> ExecutionComponent:
        """Create an ExecutionComponent for the specified execution context."""
        if execution_type.lower() == "local":
            execution_component = LocalExecutionComponent()
        elif execution_type.lower() == "sched":
            execution_component = SlurmExecutionComponent()
        else:
            logger.warning(f"Unknown execution type '{execution_type}', defaulting to local")
            execution_component = LocalExecutionComponent()
        
        return execution_component
