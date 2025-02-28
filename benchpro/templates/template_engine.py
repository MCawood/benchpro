"""
Template Engine for BenchPRO.

This module handles rendering job scripts from Jinja2 templates using configuration data.
"""

import os
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateEngine:
    """
    Renders job scripts from Jinja2 templates using configuration data.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the template engine.

        Args:
            template_dir: Directory containing template files.
        """
        if template_dir is None:
            # Look for templates in examples/input/templates
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.template_dir = os.path.join(project_root, "examples", "input", "templates")
        else:
            self.template_dir = template_dir
            
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
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
        template = self.env.get_template(template_name)
        return template.render(**config)
    
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
        rendered_content = self.render_template(template_name, config)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Write the rendered content to the output file
        with open(output_path, 'w') as f:
            f.write(rendered_content)
            
        return output_path 