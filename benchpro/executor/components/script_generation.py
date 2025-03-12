"""
Script Generation Components for BenchPRO Task composition.

This module defines components for generating execution scripts from templates.
"""

import os
from typing import Dict, Any, Optional, List

from benchpro.executor.components.interfaces import ScriptGenerationComponent, TemplateError
from benchpro.templates.template_engine import TemplateEngine
from benchpro.utils.logger import get_logger


class BaseScriptGenerator(ScriptGenerationComponent):
    """Base implementation of ScriptGenerationComponent with common functionality."""
    
    def __init__(self, template_engine: Optional[TemplateEngine] = None):
        """
        Initialize the script generator.
        
        Args:
            template_engine: Template engine to use for rendering templates.
                If None, a new instance will be created.
        """
        self.logger = get_logger(__name__)
        self.template_engine = template_engine or TemplateEngine()
    
    def prepare_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare variables for template rendering.
        
        Args:
            config: Task configuration.
            
        Returns:
            Dictionary of variables for template rendering.
        """
        self.logger.debug("Preparing template variables")
        
        # Start with a copy of the config to avoid modifying the original
        variables = dict(config)
        
        # Add any additional variables needed by templates
        variables["script_type"] = "local"  # Default to local script type
        
        return variables
        
    def _add_workspace_directory_handling(self, script_content: str) -> str:
        """
        Add commands to ensure the script runs in the workspace directory.
        
        This adds commands near the top of the script to determine its own directory
        and change to that directory before executing the rest of the script.
        
        Args:
            script_content: Original script content.
            
        Returns:
            Enhanced script content with directory handling.
        """
        self.logger.debug("Adding workspace directory handling to script")
        
        # Split the script to insert directory change after shebang and before other commands
        script_lines = script_content.splitlines()
        if not script_lines:
            return script_content
        
        # Prepare the commands to add
        workspace_dir_commands = [
            "",  # Empty line for readability
            "# Get the workspace root directory (directory containing this script)",
            "SCRIPT_PATH=$0",
            "SCRIPT_DIR=$(dirname \"$SCRIPT_PATH\")",
            "# Change to workspace root directory",
            "cd \"$SCRIPT_DIR\"",
            "echo \"Working in workspace: $SCRIPT_DIR\"",
            ""  # Empty line for readability
        ]
        
        # Add directory change commands after the first line (shebang)
        enhanced_script_lines = [script_lines[0]] + workspace_dir_commands + script_lines[1:]
        enhanced_script = "\n".join(enhanced_script_lines)
        
        self.logger.debug("Workspace directory handling added to script")
        
        return enhanced_script


class LocalScriptGenerator(BaseScriptGenerator):
    """Script generator for local execution."""
    
    def generate_script(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Generate a script for local execution from a template.
        
        Args:
            template_path: Path to the template file.
            variables: Variables to use when rendering the template.
            
        Returns:
            Generated script content as a string.
            
        Raises:
            TemplateError: If the template cannot be loaded or rendered.
        """
        self.logger.debug(f"Generating local script from template: {template_path}")
        
        try:
            # Ensure script_type is set to local
            variables = dict(variables)
            variables["script_type"] = "local"
            
            # Render the template with the provided variables
            script_content = self.template_engine.render_template(template_path, variables)
            
            # Add workspace directory handling
            script_content = self._add_workspace_directory_handling(script_content)
            
            self.logger.debug("Local script generation completed successfully")
            
            return script_content
        except Exception as e:
            self.logger.error(f"Error generating local script: {str(e)}")
            raise TemplateError(f"Failed to generate local script: {str(e)}")


class SlurmScriptGenerator(BaseScriptGenerator):
    """Script generator for Slurm execution."""
    
    def generate_script(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Generate a script for Slurm execution from a template.
        
        Args:
            template_path: Path to the template file.
            variables: Variables to use when rendering the template.
            
        Returns:
            Generated script content as a string.
            
        Raises:
            TemplateError: If the template cannot be loaded or rendered.
        """
        self.logger.debug(f"Generating Slurm script from template: {template_path}")
        
        try:
            # Ensure script_type is set to slurm
            variables = dict(variables)
            variables["script_type"] = "slurm"
            
            # Generate Slurm directives
            slurm_directives = self._generate_slurm_directives(variables)
            
            # Render the template with the provided variables
            template_content = self.template_engine.render_template(template_path, variables)
            
            # Combine directives with template content
            script_content = slurm_directives + "\n\n" + template_content
            
            # Add workspace directory handling
            script_content = self._add_workspace_directory_handling(script_content)
            
            self.logger.debug("Slurm script generation completed successfully")
            
            return script_content
        except Exception as e:
            self.logger.error(f"Error generating Slurm script: {str(e)}")
            raise TemplateError(f"Failed to generate Slurm script: {str(e)}")
    
    def _generate_slurm_directives(self, variables: Dict[str, Any]) -> str:
        """
        Generate Slurm directives from job configuration.
        
        Args:
            variables: Variables containing job configuration.
            
        Returns:
            String containing Slurm directives.
        """
        self.logger.debug("Generating Slurm directives")
        
        # Get job configuration from variables
        job_config = variables.get("job", {})
        
        # Start with shebang
        directives = ["#!/bin/bash"]
        
        # Add basic job directives
        job_name = job_config.get("name", "benchpro_job")
        directives.append(f"#SBATCH -J {job_name}")
        
        # Add resource directives
        if "nodes" in job_config:
            directives.append(f"#SBATCH -N {job_config['nodes']}")
        
        if "tasks_per_node" in job_config:
            directives.append(f"#SBATCH --ntasks-per-node={job_config['tasks_per_node']}")
        
        if "time_limit" in job_config:
            directives.append(f"#SBATCH -t {job_config['time_limit']}")
        
        # Add optional directives
        if "queue" in job_config and job_config["queue"]:
            directives.append(f"#SBATCH -p {job_config['queue']}")
        
        if "account" in job_config and job_config["account"]:
            directives.append(f"#SBATCH -A {job_config['account']}")
        
        # Add output and error file directives
        workspace = variables.get("workspace", {})
        logs_dir = workspace.get("logs_dir", "logs")
        
        directives.append(f"#SBATCH -o {logs_dir}/{job_name}.%j.out")
        directives.append(f"#SBATCH -e {logs_dir}/{job_name}.%j.err")
        
        # Add any custom directives
        custom_directives = job_config.get("slurm_directives", [])
        if custom_directives:
            for directive in custom_directives:
                directives.append(f"#SBATCH {directive}")
        
        return "\n".join(directives) 