# BenchPRO Process Flows

This document outlines the key processes in BenchPRO, detailing the exact steps that occur for each operation.

## BUILD Flow

When a user issues the command:
```bash
benchpro build hello_world
```

The following sequence occurs:

### 1. Configuration Loading and Validation
```yaml
# Example templates/applications/hello_world/build.yaml
name: hello_world
version: "1.0.0"
type: application

description: |
  A simple Hello World application that demonstrates the basic build profile structure.

build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: hello_world

source:
  files:
    - hello_world.c

variables:
  MESSAGE: "Hello from BenchPro!"
  REPEAT_COUNT: 1
```

a) Read configuration file
   - Look for build.yaml in templates/applications/hello_world/
   - Parse YAML format
   - Extract build configuration and variables

b) Validate configuration
   - Check required fields exist (name, version, type)
   - Validate build configuration (compiler, binary settings)
   - Verify source files exist
   - Type check variables

### 2. Template Processing
```bash
# Example templates/applications/hello_world/build.j2
#!/bin/bash
set -e  # Exit on error

echo "Building hello_world application..."

# Setup build environment
BUILD_DIR="{{ working_dir }}"
INSTALL_DIR="{{ install_dir }}"

cd "${BUILD_DIR}"

# Export build variables
export MESSAGE="{{ variables.MESSAGE }}"
export REPEAT_COUNT="{{ variables.REPEAT_COUNT }}"

# Compile
echo "Compiling with {{ build.compiler }}..."
gcc -o {{ build.binary.executable }} hello_world.c

# Install
echo "Installing to ${INSTALL_DIR}..."
mkdir -p ${INSTALL_DIR}/{{ build.binary.directory }}
cp {{ build.binary.executable }} ${INSTALL_DIR}/{{ build.binary.directory }}/
```

a) Read template file
   - Load build.j2 from template directory
   - Verify file exists and is readable
   - Parse Jinja2 template structure

b) Process template variables
   - Create template context from config:
     * working_dir: Build directory path
     * install_dir: Installation directory
     * variables: User-defined variables
     * build: Build configuration

c) Validate processed script
   - Render template with context
   - Verify all variables were substituted
   - Check for basic shell syntax
   - Ensure no template syntax remains

### 3. Working Directory Setup
Only proceeds if steps 1 & 2 succeed:

a) Create directory structure:
```
work_dir/
├── hello_world_1.0/      # Based on code and version
    ├── build/            # Build artifacts
    ├── bin/              # Executables
    └── log/              # Build logs
```

b) Set appropriate permissions
   - Directory permissions (755)
   - Ensure user has write access

### 4. Build Script Deployment
a) Write processed script
   - Save to work_dir/hello_world_1.0/build/build.sh
   - Set executable permissions (700)
   - Preserve original template (for reference)

### 5. Execution Preparation
a) Determine execution mode
   - Check if running in local or SLURM environment
   - Set appropriate execution flags

b) Prepare environment
   - Load required modules (intel, impi)
   - Set environment variables
   - Configure build paths

### 6. Build Execution
a) Local execution:
   - Execute build.sh directly
   - Capture stdout/stderr to log file
   - Monitor process status

b) SLURM execution:
   - Generate SLURM submission script
   - Submit job
   - Monitor job status

### 7. Status Monitoring
a) Track build progress
   - Monitor log file
   - Check for error conditions
   - Update status (running, completed, failed)

b) Handle completion
   - Verify executable exists
   - Check permissions
   - Record build status

### 8. Error Handling
At each step:
- Fail fast if error detected
- Clean up any partial files/directories
- Provide clear error messages
- Log detailed error information

### 9. Success Criteria
Build is considered successful when:
1. Script executes with return code 0
2. Executable file exists and is runnable
3. No critical errors in build log
4. All required artifacts are present

### 10. Cleanup
On success:
- Preserve build logs
- Clean temporary files
- Set correct permissions

On failure:
- Preserve error logs
- Clean working directory
- Report failure reason 