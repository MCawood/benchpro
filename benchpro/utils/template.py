"""
Template utility functions for BenchPRO.

This module provides utility functions for finding and rendering templates.
"""

import os
import jinja2
from typing import Dict, Any, List, Optional

from benchpro.utils.logger import get_logger

logger = get_logger(__name__)

def find_template_file(template_path: str, search_paths: List[str]) -> Optional[str]:
    """
    Find a template file in the search paths.
    
    Args:
        template_path: Path or name of the template file.
        search_paths: List of directories to search in.
        
    Returns:
        Full path to the template file, or None if not found.
    """
    # If template_path is already a full path and exists, return it
    if os.path.isfile(template_path):
        logger.debug(f"Template file found at absolute path: {template_path}")
        return template_path
        
    # Check if template_path is a relative path in one of the search directories
    for search_dir in search_paths:
        full_path = os.path.join(search_dir, template_path)
        if os.path.isfile(full_path):
            logger.debug(f"Template file found at: {full_path}")
            return full_path
            
    # If we haven't found it yet and it doesn't have a .j2 extension, try with it
    if not template_path.endswith('.j2'):
        template_j2 = f"{template_path}.j2"
        for search_dir in search_paths:
            full_path = os.path.join(search_dir, template_j2)
            if os.path.isfile(full_path):
                logger.debug(f"Template file found with .j2 extension at: {full_path}")
                return full_path
                
    logger.warning(f"Template file not found: {template_path}")
    return None

def render_template(file_path: str, variables: Dict[str, Any], search_paths: List[str]) -> str:
    """
    Render a template with variables.
    
    Args:
        file_path: Path or name of the template file.
        variables: Variables to use in template rendering.
        search_paths: List of directories to search for the template.
        
    Returns:
        Rendered template content.
        
    Raises:
        FileNotFoundError: If the template file is not found.
        jinja2.exceptions.TemplateError: If template rendering fails.
    """
    # Find the template file
    template_file = find_template_file(file_path, search_paths)
    if not template_file:
        raise FileNotFoundError(f"Template file not found: {file_path}")
        
    # Create Jinja2 environment
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(search_paths),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )
    
    # Load the template by name (relative to search paths)
    template_name = os.path.basename(template_file)
    template = env.get_template(template_name)
    
    # Render the template
    rendered = template.render(**variables)
    
    return rendered 