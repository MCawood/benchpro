"""
Template Engine for BenchPRO.

This module handles rendering job scripts from Jinja2 templates using configuration data.
"""

import os
from typing import Dict, Any, Optional, List
from jinja2 import Environment, FileSystemLoader, select_autoescape

from benchpro.utils.user_dir import user_dir_manager, UserDirectoryManagerInterface, get_user_dir_manager
from benchpro.utils.logger import get_logger


class TemplateEngine:
    """
    Renders job scripts from Jinja2 templates using configuration data.
    """
    
    def __init__(self, template_dir: Optional[str] = None, user_dir_manager: Optional[UserDirectoryManagerInterface] = None):
        """
        Initialize the template engine.

        Args:
            template_dir: Directory containing template files.
            user_dir_manager: UserDirectoryManager instance. If None, uses the default instance.
        """
        self.logger = get_logger(__name__)
        self.logger.info("Initializing TemplateEngine")
        
        # Use the provided user_dir_manager or get the default one
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
        if template_dir is None:
            # Look for templates in ~/.benchpro/inputs
            self.template_dir = self.user_dir_manager.get_path("inputs")
            self.logger.debug(f"Using default template directory: {self.template_dir}")
            
            # Copy default templates if they don't exist
            self._copy_default_templates()
        else:
            self.template_dir = template_dir
            self.logger.debug(f"Using custom template directory: {self.template_dir}")
            
        # Initialize Jinja2 environment
        self.logger.debug("Setting up Jinja2 environment")
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.logger.debug("Jinja2 environment initialized")
        
    def _copy_default_templates(self):
        """
        Copy default templates to the user directory if they don't exist.
        """
        self.logger.debug("Checking for default templates to copy")
        
        # Get the default templates from the examples directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Use the new directory structure that matches ~/.benchpro/inputs
        example_app_templates_dir = os.path.join(project_root, "examples", "inputs", "application")
        example_bench_templates_dir = os.path.join(project_root, "examples", "inputs", "benchmark")
        
        self.logger.debug(f"Example application templates directory: {example_app_templates_dir}")
        self.logger.debug(f"Example benchmark templates directory: {example_bench_templates_dir}")
        
        # Copy application templates
        if os.path.exists(example_app_templates_dir):
            # Get all template files in the example application templates directory
            app_template_files = [f for f in os.listdir(example_app_templates_dir) if f.endswith('.j2')]
            
            if app_template_files:
                self.logger.info(f"Copying {len(app_template_files)} application templates to user directory")
                self.logger.debug(f"Application templates: {app_template_files}")
                self.user_dir_manager.copy_default_files(example_app_templates_dir, "inputs_application", app_template_files)
            else:
                self.logger.debug("No application templates found to copy")
        else:
            self.logger.debug(f"Example application templates directory not found: {example_app_templates_dir}")
            
        # Copy benchmark templates
        if os.path.exists(example_bench_templates_dir):
            # Get all template files in the example benchmark templates directory
            bench_template_files = [f for f in os.listdir(example_bench_templates_dir) if f.endswith('.j2')]
            
            if bench_template_files:
                self.logger.info(f"Copying {len(bench_template_files)} benchmark templates to user directory")
                self.logger.debug(f"Benchmark templates: {bench_template_files}")
                self.user_dir_manager.copy_default_files(example_bench_templates_dir, "inputs_benchmark", bench_template_files)
            else:
                self.logger.debug("No benchmark templates found to copy")
        else:
            self.logger.debug(f"Example benchmark templates directory not found: {example_bench_templates_dir}")
        
    def render_template(self, template_name: str, config: Dict[str, Any]) -> str:
        """
        Render a template with the provided configuration.
        
        Args:
            template_name: Name of the template file to render.
            config: Configuration dictionary to use for rendering.
            
        Returns:
            Rendered template as a string.
            
        Raises:
            jinja2.exceptions.TemplateNotFound: If the template file doesn't exist.
        """
        self.logger.info(f"Rendering template: {template_name}")
        
        # Determine the template directory based on task type
        task_type = config.get('task_type')
        if task_type == 'application':
            template_dir = self.user_dir_manager.get_path("inputs_application")
        elif task_type == 'benchmark':
            template_dir = self.user_dir_manager.get_path("inputs_benchmark")
        else:
            # If task_type is not specified, default to application
            template_dir = self.user_dir_manager.get_path("inputs_application")
        
        self.logger.debug(f"Looking for template in: {template_dir}")
        
        # Create a new environment with the appropriate loader
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        try:
            template = env.get_template(template_name)
            self.logger.debug(f"Template loaded: {template_name} from {template_dir}")
            
            rendered = template.render(**config)
            self.logger.debug(f"Template rendered successfully: {template_name}")
            
            return rendered
        except Exception as e:
            self.logger.error(f"Error rendering template {template_name}: {str(e)}")
            raise
    
    def get_template_dirs(self) -> List[str]:
        """
        Get a list of template directories.
        
        Returns:
            List of template directories.
        """
        template_dirs = []
        
        # Add application templates directory
        app_dir = self.user_dir_manager.get_path("inputs_application")
        if os.path.exists(app_dir):
            template_dirs.append(app_dir)
            
        # Add benchmark templates directory
        bench_dir = self.user_dir_manager.get_path("inputs_benchmark")
        if os.path.exists(bench_dir):
            template_dirs.append(bench_dir)
            
        # Add the default template directory
        if self.template_dir and os.path.exists(self.template_dir):
            template_dirs.append(self.template_dir)
            
        self.logger.debug(f"Template directories: {template_dirs}")
        return template_dirs
        
    def write_rendered_template(self, template_name: str, config: Dict[str, Any], 
                               output_path: str) -> str:
        """
        Render a template and write it to a file.
        
        Args:
            template_name: Name of the template file to render.
            config: Configuration dictionary to use for rendering.
            output_path: Path where the rendered template should be written.
            
        Returns:
            Path to the written file.
            
        Raises:
            jinja2.exceptions.TemplateNotFound: If the template file doesn't exist.
            IOError: If the output file cannot be written.
        """
        self.logger.info(f"Rendering and writing template {template_name} to {output_path}")
        
        rendered_content = self.render_template(template_name, config)
        
        # Ensure the directory exists
        self.logger.debug(f"Ensuring directory exists for output: {output_path}")
        self.user_dir_manager.ensure_file_directory(output_path)
        
        # Write the rendered content to the output file
        try:
            with open(output_path, 'w') as f:
                f.write(rendered_content)
                
            self.logger.info(f"Template written successfully to: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error writing template to {output_path}: {str(e)}")
            raise 