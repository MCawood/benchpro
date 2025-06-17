# BenchPRO Refactoring Implementation - Step 1: ModuleManager

## Issue Analysis

Based on our test results, we've identified several key issues with the ModuleManager component:

1. **Inconsistent function signatures**: The `create_module_file` method has been changed to take individual parameters, breaking existing tests that expect it to accept a dictionary.

2. **Interface mismatch**: The `get_module_file_path` method in ModuleManager has a different signature than the tests expect, leading to failures.

3. **Missing module file creation in registry**: The RegistryManager is no longer calling the ModuleManager to create module files, breaking tests that expect this integration.

4. **Excessive debug logging**: The ModuleManager has excessive debug output that pollutes the logs and makes troubleshooting difficult.

## Implementation Plan for ModuleManager

### 1. Fix `create_module_file` Method

We need to support both dictionary-based and parameter-based approaches:

```python
def create_module_file(self, app_data_or_name, app_version=None, workspace_dir=None, 
                      dependencies=None, binary_path=None, module_paths=None):
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
    
    # Implementation continues with the common module file creation logic
    # ...
```

### 2. Fix `get_module_file_path` Method

Make the method consistent with the WorkspaceManager's version:

```python
def get_module_file_path(self, app_name, app_version, workspace_dir):
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
```

### 3. Update `extract_dependencies_from_config` Method

Simplify and improve error handling:

```python
def extract_dependencies_from_config(self, config):
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
```

### 4. Update `extract_module_paths_from_config` Method

Similar improvements for module paths:

```python
def extract_module_paths_from_config(self, config):
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
```

### 5. Clean up Logging

Reduce debug logging to essential information:

```python
# Before:
self.logger.debug(f"Template variables: {template_vars}")

# After:
if self.logger.isEnabledFor(logging.DEBUG):
    self.logger.debug(f"Creating module file with: app={app_name}, version={app_version}")
```

### 6. Improve Template Extraction

Move the template to a separate file for better maintenance:

1. Create a new directory: `benchpro/templates/modules/`
2. Create file: `benchpro/templates/modules/module.lua.j2`
3. Update the ModuleManager to load the template from the file

## Integration with Registry Manager

Update the Registry Manager to call the ModuleManager to create module files:

```python
def register_application(self, app_data):
    # ... existing code ...
    
    # Create a module file if possible
    if all(field in app_data for field in ["name", "version", "workspace_dir", "binary_path"]):
        try:
            from benchpro.workspace.module_manager import ModuleManager
            module_manager = ModuleManager()
            
            module_file_path = module_manager.create_module_file(app_data)
            app_data_copy["module_file"] = module_file_path
            
            self.logger.info(f"Created module file: {module_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to create module file: {str(e)}")
            # Continue registration even if module file creation fails
    
    # ... rest of method ...
```

## Test Update Plan

1. Fix `test_module_manager.py` to match the new implementation:
   - Update assertions to match new function signatures
   - Update mock objects to handle both dictionary and parameter input

2. Fix `test_registry_manager_env.py` to match new registry-module integration:
   - Update mocks to verify correct parameter passing
   - Fix assertions for module file creation

## Implementation Steps

1. Implement the updated ModuleManager methods
2. Update Registry Manager integration
3. Fix unit tests for ModuleManager
4. Fix unit tests for Registry Manager
5. Run integration tests to verify the changes work together 