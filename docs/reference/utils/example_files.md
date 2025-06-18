# Example Files and Synchronization

## Overview

BenchPRO uses a dual-directory system for example files that allows developers to maintain master copies in the project repository while providing users with working copies in their local BenchPRO directory. This system ensures that example files can be updated and distributed while allowing users to customize their local copies without affecting the originals.

## Directory Structure

### Master Files (Project Directory)
```
benchpro_2.0/
└── examples/
    └── inputs/
        ├── application/
        │   ├── hello_world.yaml
        │   └── hello_world.j2
        ├── benchmark/
        │   ├── hello_world.yaml
        │   └── hello_world.j2
        └── source/
            └── hello_world.c
```

### User Files (Local BenchPRO Directory)
```
~/.benchpro/
└── inputs/
    ├── application/
    │   ├── hello_world.yaml
    │   └── hello_world.j2
    ├── benchmark/
    │   ├── hello_world.yaml
    │   └── hello_world.j2
    └── source/
        └── hello_world.c
```

## Synchronization Process

### Automatic Synchronization

The UserDirectoryManager automatically copies example files during initialization:

1. **On First Run**: When BenchPRO initializes, it automatically copies all example files from the project's `examples/` directory to the user's `~/.benchpro/` directory.

2. **Version Checking**: The system compares file modification times and only copies newer files, preserving user customizations.

3. **File Types**: The synchronization includes:
   - `.yaml` and `.yml` files (configuration profiles)
   - `.j2` files (Jinja2 templates)
   - Source code files (`.c`, `.cpp`, `.f90`, `.f`, `.py`, `.h`, `.hpp`)

### Manual Synchronization

Users can manually synchronize files using the CLI:

```bash
# Synchronize example files, preserving newer user files
bp init

# Force synchronization, overwriting all user files
bp init --force
```

### Implementation Details

The synchronization is handled by the `UserDirectoryManager` class:

```python
def copy_example_profiles(self, force: bool = False) -> bool:
    """Copy example profiles to user directories."""
    
def copy_default_source_files(self, force: bool = False) -> bool:
    """Copy default source files to user directories."""
```

## Configuration Schema Compliance

### Critical Requirement

**All example files must comply with the current configuration schemas.** This is essential because:

1. Example files serve as the default configurations users start with
2. Schema validation occurs during task execution
3. Non-compliant examples will cause immediate failures

### Schema Mismatch Example

We recently encountered an issue where the `hello_world.yaml` example used an object format for modules:

```yaml
# ❌ Incorrect format (object-based)
environment:
  modules:
    - name: intel
      version: "24.0"
    - name: impi
      version: "21.11"
```

But the schema expected simple strings:

```python
# Schema definition
modules: List[str] = Field(default_factory=list)
```

The correct format is:

```yaml
# ✅ Correct format (string-based)
environment:
  modules:
    - "intel/24.0"
    - "impi/21.11"
```

### Validation Process

The configuration validator checks example files against schemas in `benchpro/config/schema/`:
- `application.py` - Application configuration schema
- `benchmark.py` - Benchmark configuration schema

## Best Practices

### For Developers

1. **Always Validate**: Test any changes to example files with `bp build <profile> --dry-run` to ensure schema compliance.

2. **Update Master Files**: Make changes to files in `examples/inputs/` directory, not in `~/.benchpro/`.

3. **Synchronize After Changes**: Run `bp init --force` after updating master files to propagate changes.

4. **Schema Awareness**: Understand the current schema requirements before modifying example configurations.

5. **Test Multiple Profiles**: If changing schemas, test all example profiles to ensure compatibility.

### For Users

1. **Backup Customizations**: Before running `bp init --force`, backup any custom configurations.

2. **Use Dry Run**: Test configurations with `--dry-run` before actual execution.

3. **Check Parameter Reports**: Use `--param-report` to understand configuration sources and values.

## Troubleshooting

### Common Issues

1. **Schema Validation Errors**
   ```
   Task config error at environment.modules.0: Input should be a valid string
   ```
   - **Cause**: Configuration format doesn't match schema expectations
   - **Solution**: Update example files to use correct format and synchronize

2. **Missing Example Files**
   - **Cause**: User directory not properly initialized
   - **Solution**: Run `bp init` to copy example files

3. **Outdated Example Files**
   - **Cause**: Local files are older than master files
   - **Solution**: Run `bp init --force` to update all files

### Debugging Steps

1. **Check File Timestamps**: Compare modification times between master and user files
2. **Validate Configuration**: Use `bp build <profile> --param-report --dry-run`
3. **Review Logs**: Check BenchPRO logs for synchronization messages
4. **Manual Inspection**: Compare master and user file contents directly

## Technical Implementation

### Key Components

- **UserDirectoryManager**: Handles directory creation and file synchronization
- **ConfigValidator**: Validates configurations against schemas
- **FileSystem Abstraction**: Provides consistent file operations across environments

### Synchronization Logic

```python
def copy_default_files(self, source_dir: str, dest_dir_key: str, 
                      files: List[str], force: bool = False) -> bool:
    # Check file existence and modification times
    # Copy only if source is newer or force=True
    # Handle errors gracefully
```

### File Discovery

The system automatically discovers example files by:
1. Finding the project root directory
2. Looking for `examples/inputs/` subdirectories
3. Filtering files by relevant extensions
4. Maintaining directory structure in user space

## Future Enhancements

### Planned Improvements

1. **Selective Synchronization**: Allow users to sync specific files or profiles
2. **Conflict Resolution**: Better handling of conflicting local customizations
3. **Version Tracking**: Track which version of examples was last synchronized
4. **Schema Migration**: Automatic migration of example files when schemas change

### Integration Opportunities

1. **CI/CD Integration**: Automatic validation of example files in build pipelines
2. **Template Generation**: Generate example files from schema definitions
3. **User Notifications**: Alert users when newer example files are available 