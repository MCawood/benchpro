"""
Script Generators for BenchPRO using template composition.

This module defines script generators that implement the ScriptGenerationComponent
interface using the template composition engine.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import importlib
import os

# Import our template system components
from benchpro.templates.blocks import FileTemplateBlock, TemplateError
from benchpro.templates.composition import TemplateCompositionEngine
from benchpro.templates.standard_blocks import (
    register_standard_blocks, PRIORITY_USER_COMMANDS
)
from benchpro.utils.logger import get_logger
from benchpro.utils import template as template_utils

logger = get_logger(__name__)

# Define the ScriptGenerationComponent interface here to avoid circular imports
class ScriptGenerationComponent(ABC):
    """
    Interface for components that generate execution scripts.
    
    ScriptGenerationComponent implementations are responsible for generating
    scripts from templates, with variables populated from the task configuration.
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
            
        Raises:
            TemplateError: If the template cannot be loaded or rendered.
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


class ComposableScriptGenerator(ScriptGenerationComponent):
    """
    Script generator that uses template composition.
    
    This generator composes scripts from a library of template blocks,
    allowing for modular and context-aware script generation.
    """
    
    def __init__(self, execution_context: str):
        """
        Initialize the composable script generator.
        
        Args:
            execution_context: The execution context (e.g., "local", "slurm")
        """
        self.execution_context = execution_context
        self.composition_engine = TemplateCompositionEngine()
        self.logger = get_logger(__name__)
        
        # Register standard blocks
        register_standard_blocks(self.composition_engine, execution_context)
        
        self.logger.debug(f"Initialized composable script generator for context: {execution_context}")
    
    def prepare_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare variables for template rendering.
        
        Args:
            config: Task configuration
            
        Returns:
            Dictionary of variables for template rendering
        """
        self.logger.debug("Preparing template variables")
        
        # Start with a copy of the config to avoid modifying the original
        variables = dict(config)
        
        # Add execution context to variables
        variables["execution_context"] = self.execution_context
        
        # Check if 'system' is specified as a string and ensure the system config is accessible
        # This handles the case where system is specified via CLI as --system darwin
        system_name = variables.get('system')
        if isinstance(system_name, str):
            self.logger.debug(f"System specified as '{system_name}', ensuring system configuration is accessible")
            
            # If system configuration is loaded under a 'system' key in the configuration,
            # make it directly accessible for the template
            if 'system' not in variables or not isinstance(variables['system'], dict):
                # Set up a default structure if not present
                variables['system'] = {
                    'name': system_name,
                    'description': f"{system_name.capitalize()} System",
                    'type': system_name
                }
            
            # Make sure system name is set in the system dictionary
            else:
                if isinstance(variables['system'], dict) and 'name' not in variables['system']:
                    variables['system']['name'] = system_name
            
            # Ensure environment.variables.SYSTEM_TYPE is set correctly
            if 'environment' not in variables:
                variables['environment'] = {}
            if 'variables' not in variables['environment']:
                variables['environment']['variables'] = {}
            
            # Always set SYSTEM_TYPE to match the system name when specified via CLI or config
            # This ensures the template can access {{ environment.variables.SYSTEM_TYPE }}
            variables['environment']['variables']['SYSTEM_TYPE'] = system_name
            self.logger.debug(f"Setting environment.variables.SYSTEM_TYPE to {system_name}")
        
        # Log the variables for debugging
        self.logger.debug(f"Template variables prepared: {variables.get('system', {})}")
        self.logger.debug(f"Environment variables: {variables.get('environment', {}).get('variables', {})}")
        
        return variables
    
    def generate_script(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Generate a script using a template and the composition engine.
        
        Args:
            template_path: Path to the user template file
            variables: Variables to substitute in the template
            
        Returns:
            The generated script content.
            
        Raises:
            TemplateError: If template rendering fails.
        """
        self.logger.debug(f"Generating script for execution context '{self.execution_context}' from template: {template_path}")
        
        # Import user_dir_manager here to avoid circular imports
        from benchpro.utils.user_dir import user_dir_manager
        
        try:
            # Determine task type from variables if possible
            task_type = variables.get("task_type", self.execution_context)
            
            # Define search paths for templates - simplified to only use input directories
            search_paths = []
            
            # Add only the appropriate input directory based on task type
            if task_type == "application":
                # Only search in inputs/application directory
                inputs_app_dir = os.path.join(user_dir_manager.get_path("inputs"), "application")
                self.logger.debug(f"Using application template directory: {inputs_app_dir}")
                search_paths.append(inputs_app_dir)
            
            elif task_type == "benchmark":
                # Only search in inputs/benchmark directory
                inputs_bench_dir = os.path.join(user_dir_manager.get_path("inputs"), "benchmark")
                self.logger.debug(f"Using benchmark template directory: {inputs_bench_dir}")
                search_paths.append(inputs_bench_dir)
            
            else:
                # Fallback for unknown task types (shouldn't happen)
                self.logger.warning(f"Unknown task type: {task_type}, using both template directories")
                
                # Add both input directories as fallback
                inputs_app_dir = os.path.join(user_dir_manager.get_path("inputs"), "application")
                inputs_bench_dir = os.path.join(user_dir_manager.get_path("inputs"), "benchmark")
                search_paths.extend([inputs_app_dir, inputs_bench_dir])
            
            # Also add the directory containing the template_path if it's a file path
            template_dir = os.path.dirname(template_path)
            if template_dir and os.path.isdir(template_dir):
                search_paths.append(template_dir)
                
            self.logger.debug(f"Template search paths for task type '{task_type}': {search_paths}")
            
            # Find the template file
            full_template_path = template_utils.find_template_file(template_path, search_paths)
            if not full_template_path:
                raise TemplateError(f"Template file not found: {template_path}")
            
            # Store the resolved template path in the variables for later use
            if "_metadata" not in variables:
                variables["_metadata"] = {}
            variables["_metadata"]["template_path"] = full_template_path
            self.logger.debug(f"Stored resolved template path in metadata: {full_template_path}")
            
            # Create a FileTemplateBlock for the user template
            user_template_block = FileTemplateBlock(
                name="user_template",
                file_path=full_template_path,
                priority=PRIORITY_USER_COMMANDS,  # Use the same priority as user commands
                description="User-provided template content",
                search_paths=search_paths
            )
            
            # Register the user template block with the composition engine
            self.composition_engine.register_block(user_template_block)
            
            # Use the composition engine to generate the script
            self.logger.info(f"Using composition engine to generate script from template: {full_template_path}")
            rendered_content = self.composition_engine.compose(variables, self.execution_context)
            
            # Remove the user template block after rendering to avoid affecting future renders
            self.composition_engine.unregister_block("user_template")
            
            return rendered_content
            
        except Exception as e:
            error_msg = f"Error rendering template {template_path}: {str(e)}"
            self.logger.error(error_msg)
            raise TemplateError(error_msg)


class LocalScriptGenerator(ComposableScriptGenerator):
    """Script generator for local execution."""
    
    def __init__(self):
        """Initialize a local script generator."""
        super().__init__(execution_context="local")


class SlurmScriptGenerator(ComposableScriptGenerator):
    """Script generator for SLURM execution."""
    
    def __init__(self):
        """Initialize a SLURM script generator."""
        super().__init__(execution_context="slurm") 