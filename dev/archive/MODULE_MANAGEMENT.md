# Module Management in BenchPro 2.0

## Overview

A core component of BenchPro is the dependency structure between applications and benchmarks. The ability to build an application once and then run multiple dependent benchmarks using that single application is very useful, as it eliminates the need to rebuild base applications for every benchmark. This feature sets BenchPro apart from other similar utilities.

This document outlines the implementation plan for the module management system in BenchPro 2.0, which will enable the creation of Lmod environment module files as part of the application build process.

## What are Environment Modules?

Environment modules (specifically Lmod) allow users to dynamically modify their shell environment to use specific applications or libraries. For BenchPro, module files serve several purposes:

1. They enable benchmarks to access application binaries without needing to fully specify paths
2. They configure the environment with necessary libraries and dependencies
3. They establish a clean separation between applications and their dependent benchmarks

## Requirements

1. **Module file generation only for applications**: Module files should only be created for application tasks, not benchmark tasks
2. **Storage location**: Module files should be stored at `[workspace_dir]/modulefiles/[app_name]/[app_version].lua`
3. **PATH configuration**: The module file should prepend the workspace root directory to the PATH environment variable to ensure binaries are locatable
4. **Dependency management**: The module file should load any dependencies required by the application
5. **Error handling**: Failing to create a modulefile should be treated as a critical error
6. **Application registry**: Module file status should be reported in the `bp apps info` command

## Implementation Phases

We will implement this feature in two phases:

### Phase 1: Module File Creation
- Implement the core `ModuleManager` component
- Create and integrate module file creation with application tasks
- Create a minimal module file template with PATH settings
- Add basic workspace directory environment variable (BP_[CODE_NAME]_DIR)
- Add error handling for module file creation failures
- Update the application registry to check for module file existence

### Phase 2: Module Dependencies Support
- Add YAML configuration support for specifying module dependencies
- Support compiler, MPI implementation, and other dependency modules
- Implement the `depends_on` functionality in module files
- Update the module file template to load dependencies
- Enhance error handling for dependency resolution

## Implementation Plan

### 1. Create a Module Manager Component

We will create a new module called `module_manager.py` in the appropriate directory with the following core functionality:

- `ModuleManager` class responsible for:
  - Creating module files
  - Managing module paths
  - Providing interfaces for other components to request module file creation

### 2. Integration with Task System

The module file creation will be integrated with the existing task system using the following approach:

- Add module file creation as part of the application task completion process
- Use composition pattern to maintain clean separation of concerns
- Avoid conditional checks (if-statements) by leveraging the existing class inheritance structure

### 3. Module File Template

Create a Jinja2 template for the Lmod module file with placeholders for:
- Application name and version
- Binary/installation paths
- Dependencies and environment variables
- Description and metadata

### 4. Implementation Steps

1. **Create the Module Manager Component**
   - Implement the `ModuleManager` class 
   - Define interfaces for module file creation and management
   - Create utility functions for path manipulation and validation

2. **Enhance Application Task**
   - Add a method in the `Application` class to create module files upon successful build
   - Ensure this functionality is not present in the `Benchmark` class
   - Extract necessary information from application config to populate module template

3. **Create Module File Template**
   - Design the Lua template for Lmod module files
   - Include standard module commands (prepend_path, setenv, etc.)
   - Make the template configurable for different application types

4. **Integration with Task Orchestrator**
   - Update `TaskOrchestrator` to initialize and use the Module Manager
   - Call module creation functions at the appropriate point in the workflow
   - Implement proper error handling (critical failures)

5. **Update Application Registry Integration**
   - Modify the registry manager to include modulefile status
   - Update `bp apps info` command to show module file presence

### 5. Testing Strategy

1. **Unit Tests**
   - Test module file content generation
   - Test path resolution and directory creation
   - Test template rendering
   - Test error handling

2. **Integration Tests**
   - Test the entire workflow from application build to module file creation
   - Test loading the generated module file and verifying environment changes
   - Test benchmark dependency on application modules

3. **System Tests**
   - Verify real application builds create working module files
   - Test the interaction with the actual Lmod installation available on the local system
   - Create test modules to demonstrate benchpro module loading works

## Implementation Status

### Phase 1 (Completed)

The following components have been implemented:

1. **ModuleManager Class**
   - Created `module_manager.py` in the workspace directory
   - Implemented methods for creating and verifying module files
   - Added path resolution for module files
   - Integrated error handling with ModuleError exception

2. **Application Task Integration**
   - Updated the `Application` class to create module files
   - Ensured module file creation happens after successful task execution
   - Added proper error handling with critical failures

3. **Module File Template**
   - Created a basic module file template with PATH and environment variable settings
   - Used Jinja2 for template rendering
   - Added standard Lmod commands (whatis, prepend_path, setenv)

4. **Registry Integration**
   - Updated `RegistryFormatter` to check for module file existence
   - Added module file information to the application details view
   - Included usage instructions for loading the module

5. **Testing**
   - Created unit tests for the ModuleManager class
   - Added integration tests for the module file creation workflow

### Phase 2 (Todo)

The following tasks are planned for Phase 2:

1. **Module Dependencies**
   - Add support for specifying required modules in application YAML configuration
   - Update the YAML schema to include compiler, MPI implementation, and other module dependencies
   - Update the module file template to use `depends_on` for declaring dependencies

2. **YAML Configuration**
   - Create schema updates for module dependencies
   - Update config validation components
   - Update application configuration loading

3. **Benchmark Integration**
   - Enhance benchmark tasks to load application modules
   - Update script generation to include module loading commands

## Conclusion

The module management implementation will enhance BenchPro's functionality by creating clear interfaces between built applications and their dependent benchmarks. By using environment modules, we establish a clean, standardized way for benchmarks to access applications without tightly coupling them to specific filesystem paths.

This implementation follows best practices by:
- Using composition over inheritance
- Keeping components focused and single-purpose
- Establishing clear interfaces between systems
- Following the existing architectural patterns in BenchPro 2.0
- Implementing a phased approach to deliver value incrementally

### Next Steps After Phase 2

Once the core module file creation functionality and dependency support are implemented, we can consider:

1. Enhancing module files with additional environment variables
2. Adding support for hierarchical dependencies
3. Implementing module version conflict resolution
4. Creating a module search and discovery feature 