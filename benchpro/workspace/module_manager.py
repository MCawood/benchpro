"""
Module Manager for BenchPRO.

This module provides functionality for creating and managing environment module files.
"""

import os
import logging
import datetime
from typing import Dict, Any, Optional, List, Union

from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.utils.user_dir import get_user_dir_manager
from jinja2 import Environment, FileSystemLoader, Template, StrictUndefined


class ModuleError(Exception):
    """Exception raised for module-related errors."""
    pass


class ModuleManager:
    """
    Manages the creation and validation of environment module files.
    
    Responsibilities:
    - Create module files for applications
    - Validate module file structure
    - Provide path resolution for module files
    """
    
    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        """
        Initialize the ModuleManager.
        
        Args:
            workspace_manager: WorkspaceManager instance. If None, uses a default instance.
        """
        self.logger = logging.getLogger(__name__)
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.user_dir_manager = get_user_dir_manager()
        
        # Define the module file template content
        self.module_template = """-- {{ app_name }} {{ app_version }} module file created by BenchPro
-- Created on {{ creation_date }}

local name = "{{ app_name }}"
local version = "{{ app_version }}"

-- Description
whatis("Name: {{ app_name }}")
whatis("Version: {{ app_version }}")
whatis("Description: Application built by BenchPro")

-- Load dependencies
{% if module_paths and module_paths|length > 0 -%}
{%- for path in module_paths %}
prepend_path("MODULEPATH", "{{ path }}")
{%- endfor %}
{% endif -%}
{%- if dependencies and dependencies|length > 0 %}
{%- for dep in dependencies %}
{%- if dep is mapping and 'name' in dep %}
{%- if 'version' in dep and dep.version %}
depends_on("{{ dep.name }}/{{ dep.version }}"){% if 'description' in dep and dep.description %} -- {{ dep.description }}{% endif %}
{%- else %}
depends_on("{{ dep.name }}"){% if 'description' in dep and dep.description %} -- {{ dep.description }}{% endif %}
{%- endif %}
{%- elif dep is string %}
depends_on("{{ dep }}")
{%- endif %}
{%- endfor %}
{%- endif %}

-- Add application binary directory to PATH
prepend_path("PATH", "{{ binary_path }}")

-- Set environment variables
setenv("BP_{{ app_name_upper }}_DIR", "{{ workspace_dir }}")
"""
        
    def create_module_file(self, app_data_or_name: Union[Dict[str, Any], str], 
                          app_version: Optional[str] = None, 
                          workspace_dir: Optional[str] = None, 
                          dependencies: Optional[List[Dict[str, Any]]] = None, 
                          binary_path: Optional[str] = None,
                          module_paths: Optional[List[str]] = None) -> str:
        """
        Create a Lua module file for an application.
        
        Accepts either a dictionary with application data OR individual parameters.
        
        Args:
            app_data_or_name: Either application data dictionary or application name
            app_version: Application version (required if app_data_or_name is a string)
            workspace_dir: Path to the workspace directory (required if app_data_or_name is a string)
            dependencies: List of module dependencies (required if app_data_or_name is a string)
            binary_path: Path to the application binary (required if app_data_or_name is a string)
            module_paths: Optional list of module paths to prepend to MODULEPATH
                
        Returns:
            Path to the created module file
            
        Raises:
            ModuleError: If module file creation fails
        """
        # Handle dictionary input
        if isinstance(app_data_or_name, dict):
            app_data = app_data_or_name
            
            # Extract required fields
            app_name = app_data.get('name')
            app_version = app_data.get('version', '1.0')
            workspace_dir = app_data.get('workspace_dir')
            binary_path = app_data.get('binary_path')
            
            # Check for required fields
            if not all([app_name, workspace_dir, binary_path]):
                raise ModuleError("Missing required fields in application data")
                
            # Extract dependencies if available
            if "environment" in app_data and "modules" in app_data["environment"]:
                dependencies = app_data["environment"]["modules"]
            else:
                dependencies = []
                
            # Extract module paths if available
            if "environment" in app_data and "module_paths" in app_data["environment"]:
                module_paths = app_data["environment"]["module_paths"]
            else:
                module_paths = []
        else:
            # Direct parameter input
            app_name = app_data_or_name
            
            # Check for required fields
            if not all([app_name, app_version, workspace_dir, binary_path]):
                raise ModuleError("Missing required parameters for module file creation")
                
            # Use provided dependencies
            dependencies = dependencies or []
            module_paths = module_paths or []
        
        self.logger.info(f"Creating module file for {app_name}/{app_version}")
        
        # Ensure workspace_dir is an absolute path
        if not os.path.isabs(workspace_dir):
            workspace_dir = os.path.abspath(workspace_dir)
            
        # Get the module file path
        module_file_path = self.get_module_file_path(app_name, app_version, workspace_dir)
        
        # Create directory
        module_dir = os.path.dirname(module_file_path)
        try:
            os.makedirs(module_dir, exist_ok=True)
        except Exception as e:
            error_msg = f"Failed to create module directory {module_dir}: {str(e)}"
            self.logger.error(error_msg)
            raise ModuleError(error_msg)
            
        # Process dependencies to ensure proper format
        processed_dependencies = []
        for dep in dependencies:
            if isinstance(dep, dict):
                if "name" in dep:
                    # Copy just the necessary fields
                    dep_copy = {"name": dep["name"]}
                    if "version" in dep:
                        dep_copy["version"] = dep["version"]
                    if "description" in dep:
                        dep_copy["description"] = dep["description"]
                    processed_dependencies.append(dep_copy)
            elif isinstance(dep, str):
                # Handle string module names
                if '/' in dep:
                    name, version = dep.split('/', 1)
                    processed_dependencies.append({"name": name, "version": version})
                else:
                    processed_dependencies.append({"name": dep})
                    
        # Process module paths
        processed_module_paths = []
        for path in module_paths or []:
            if isinstance(path, str):
                # Ensure path is absolute
                if not os.path.isabs(path):
                    path = os.path.abspath(path)
                processed_module_paths.append(path)
                
        # Prepare template variables
        template_vars = {
            "app_name": app_name,
            "app_version": app_version,
            "app_name_upper": app_name.upper(),
            "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "workspace_dir": workspace_dir,
            "binary_path": os.path.dirname(binary_path) if os.path.isabs(binary_path) else workspace_dir,
            "dependencies": processed_dependencies,
            "module_paths": processed_module_paths
        }
        
        # Render the template
        try:
            template = Template(self.module_template)
            module_content = template.render(**template_vars)
            
            # Ensure the rendered content ends with a newline
            if not module_content.endswith('\n'):
                module_content += '\n'
                
        except Exception as e:
            error_msg = f"Failed to render module file template: {str(e)}"
            self.logger.error(error_msg)
            raise ModuleError(error_msg)
            
        # Write the module file
        try:
            with open(module_file_path, 'w') as f:
                f.write(module_content)
            self.logger.info(f"Created module file: {module_file_path}")
        except Exception as e:
            error_msg = f"Failed to write module file to {module_file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ModuleError(error_msg)
            
        # Verify the created file
        if not self.verify_module_file(module_file_path):
            error_msg = f"Created module file is invalid: {module_file_path}"
            self.logger.error(error_msg)
            raise ModuleError(error_msg)
            
        return module_file_path
        
    def extract_dependencies_from_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract module dependencies from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of module dependencies (each a dict with 'name' and optional 'version')
        """
        dependencies = []
        
        if not isinstance(config, dict):
            return dependencies
            
        if "environment" in config and "modules" in config["environment"]:
            modules = config["environment"]["modules"]
            
            if not isinstance(modules, list):
                return dependencies
                
            for module in modules:
                if isinstance(module, dict):
                    if "name" in module:
                        # Copy just the necessary fields
                        dep = {"name": module["name"]}
                        if "version" in module:
                            dep["version"] = module["version"]
                        dependencies.append(dep)
                elif isinstance(module, str):
                    # Handle string module names
                    if '/' in module:
                        name, version = module.split('/', 1)
                        dependencies.append({"name": name, "version": version})
                    else:
                        dependencies.append({"name": module})
                        
        return dependencies
    
    def extract_module_paths_from_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Extract module paths from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of module paths
        """
        module_paths = []
        
        if not isinstance(config, dict):
            return module_paths
            
        if "environment" in config and "module_paths" in config["environment"]:
            paths = config["environment"]["module_paths"]
            
            if not isinstance(paths, list):
                return module_paths
                
            for path in paths:
                if isinstance(path, str):
                    # Ensure path is absolute
                    if not os.path.isabs(path):
                        path = os.path.abspath(path)
                    module_paths.append(path)
                    
        return module_paths
    
    def get_module_file_path(self, app_name: str, app_version: str, workspace_dir: str) -> str:
        """
        Get the path to a module file.
        
        Args:
            app_name: Application name
            app_version: Application version
            workspace_dir: Workspace directory path
            
        Returns:
            Path to the module file
        """
        # Create the path as [workspace_dir]/modulefiles/[app_name]/[app_version].lua
        module_file_path = os.path.join(
            workspace_dir, 
            "modulefiles", 
            app_name, 
            f"{app_version}.lua"
        )
        
        return module_file_path
            
    def verify_module_file(self, module_file_path: str) -> bool:
        """
        Verify that a module file exists and contains required components.
        
        Args:
            module_file_path: Path to the module file
            
        Returns:
            True if the module file is valid, False otherwise
        """
        if not os.path.exists(module_file_path):
            self.logger.error(f"Module file does not exist: {module_file_path}")
            return False
            
        try:
            with open(module_file_path, 'r') as f:
                content = f.read()
                
            # Check for required components
            required_components = [
                "whatis",
                "local name",
                "local version",
                "prepend_path"
            ]
            
            for component in required_components:
                if component not in content:
                    self.logger.error(f"Module file missing required component '{component}': {module_file_path}")
                    return False
                    
            return True
        except Exception as e:
            self.logger.error(f"Error verifying module file {module_file_path}: {str(e)}")
            return False
            
    def validate_modules(self, modules: List[Dict[str, Any]], module_paths: Optional[List[str]] = None) -> tuple:
        """
        Validate module dependencies and paths.
        
        Args:
            modules: List of module dependencies
            module_paths: Optional list of module paths
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation - just check that the lists contain dictionaries and strings
        valid = True
        error_message = ""
        
        # Validate modules
        if modules:
            for i, module in enumerate(modules):
                if not isinstance(module, (dict, str)):
                    valid = False
                    error_message = f"Module at index {i} has invalid type: {type(module)}"
                    break
                
                if isinstance(module, dict) and "name" not in module:
                    valid = False
                    error_message = f"Module at index {i} is missing required 'name' field"
                    break
                    
        # Validate module paths
        if module_paths:
            for i, path in enumerate(module_paths):
                if not isinstance(path, str):
                    valid = False
                    error_message = f"Module path at index {i} has invalid type: {type(path)}"
                    break
                    
        return valid, error_message 