# Workspace Manager

The `WorkspaceManager` class is responsible for managing workspace directories and files in BenchPRO. It provides a unified interface for creating, accessing, and manipulating files and directories within a workspace.

## Overview

A workspace in BenchPRO is a directory structure where all files related to a task are stored. The `WorkspaceManager` ensures this structure is consistent across different task types and provides methods to access various parts of the workspace.

## Workspace Directory Structure

A typical BenchPRO workspace has the following structure:

```
workspace_dir/
├── application_build.sh    # Application build script
├── binary_executable       # Compiled application
├── inputs/                 # Input files
│   ├── application.yaml    # Original application configuration
│   └── template.j2         # Template used for script generation
├── logs/                   # Log files
│   └── benchpro_debug.log  # Debug logs
├── modulefiles/            # Module files
│   └── app_name/
│       └── version.lua     # Environment module file
└── source_files            # Source code
```

## Key Responsibilities

The `WorkspaceManager` has several key responsibilities:

1. **Creating workspace directories**:  
   Creates the base workspace directory and all required subdirectories.

2. **Copying files to the workspace**:  
   Copies configuration files, templates, and source files to the workspace.

3. **Managing workspace paths**:  
   Provides methods to get absolute paths to various parts of the workspace.

4. **Supporting module file creation**:  
   Works with the `ModuleManager` to create and manage environment module files.

## Integration with ModuleManager

The `WorkspaceManager` and `ModuleManager` work together to manage workspaces and module files:

1. `WorkspaceManager` creates the workspace directory structure, including the `modulefiles` directory.
2. `WorkspaceManager.get_module_file_path()` determines the path where module files should be created.
3. `ModuleManager` uses these paths to create and manage module files.

## API Reference

### Methods

- **create_workspace(task_type, task_name)**:  
  Creates a new workspace directory for a task of the given type.

- **copy_profile_file(profile_path, workspace_dir)**:  
  Copies a profile file to the workspace's inputs directory.

- **copy_log_file(log_file_path, workspace_dir)**:  
  Copies a log file to the workspace's logs directory.

- **copy_template_file(template_path, workspace_dir)**:  
  Copies a template file to the workspace's inputs directory.

- **get_module_file_path(workspace_dir, app_name, app_version)**:  
  Gets the path to a module file in the workspace.

- **get_script_path(workspace_dir, script_name)**:  
  Gets the path to a script in the workspace.

## Workspace Configuration

The workspace configuration is stored in the task configuration under the `workspace` key:

```yaml
workspace:
  base_input_dir: "examples/input"
  base_output_dir: "examples/output"
  keep_build: true
  keep_build_files: true
  keep_logs: true
  keep_source: true
  workspace_dir: "/path/to/workspace"
```

This configuration is used by the `WorkspaceManager` to determine how to create and manage the workspace.

## Lifecycle of a Workspace

1. **Creation**:  
   The `TaskOrchestrator` calls `WorkspaceManager.create_workspace()` to create a new workspace.

2. **Configuration**:  
   The workspace path is added to the task configuration.

3. **File Population**:  
   Configuration files, templates, and source files are copied to the workspace.

4. **Task Execution**:  
   The task is executed in the workspace, potentially creating new files.

5. **Module File Creation**:  
   For application tasks, a module file is created in the workspace's `modulefiles` directory.

6. **Registration**:  
   The workspace is registered with the application registry.

## Best Practices

When working with workspaces in BenchPRO:

1. **Use the WorkspaceManager API**:  
   Always use the `WorkspaceManager` methods to access workspace paths rather than constructing them manually.

2. **Preserve workspace_dir**:  
   When loading configuration, preserve the `workspace_dir` to ensure consistent access to workspace files.

3. **Clean up when appropriate**:  
   Use the workspace configuration options to control which files are kept after task execution.

## Related Documentation

- [Module Manager](module_manager.md): Works with the WorkspaceManager to create and manage module files
- [Task Orchestrator](../executor/task_composition.md): Orchestrates task execution using workspaces 