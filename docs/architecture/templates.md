# Template System Architecture

## Overview

The BenchPRO template system provides a flexible and extensible way to define and execute benchmark tasks. It uses a combination of YAML configuration and Jinja2-style templates to support:
- Application build scripts
- Benchmark execution scripts
- Resource configuration
- Environment setup

## Components

### 1. Template Loader
- Discovers and loads templates from configured directories
- Validates template structure and configuration
- Manages template versioning and dependencies

### 2. Template Configuration
- YAML-based configuration format
- Validates required fields and data types
- Supports variable definitions and overrides
- Handles version management

### 3. Template Renderer
- Processes templates using Jinja2-style syntax
- Supports variable substitution and conditionals
- Provides error handling and validation
- Manages template context and environment

## Template Structure

### Directory Layout
```
templates/
├── applications/
│   └── app_name/
│       ├── config.yaml
│       ├── build.j2
│       └── run.j2
└── benchmarks/
    └── bench_name/
        ├── config.yaml
        ├── setup.j2
        └── run.j2
```

### Configuration Format
```yaml
name: template_name
version: 1.0.0
type: application|benchmark
description: Template description

build:
  language: c|cpp|fortran
  compiler: gcc|intel|pgi
  binary:
    directory: bin
    executable: app_name

source:
  files:
    - src/main.c
    - src/util.c

variables:
  COMPILER_FLAGS: "-O3 -march=native"
  MPI_PROCS: 4
```

### Template Syntax
```bash
#!/bin/bash
# Template variables
export COMPILER="{{ build.compiler }}"
export FLAGS="{{ variables.COMPILER_FLAGS }}"

# Dynamic content
{% if build.language == "c" %}
$COMPILER $FLAGS -o {{ build.binary.executable }} {{ source.files|join(" ") }}
{% endif %}

# Error handling
{% if not build.binary.executable %}
echo "Error: No executable specified"
exit 1
{% endif %}
```

## Variable Substitution

### Context Variables
- `build`: Build configuration settings
- `source`: Source file information
- `variables`: User-defined variables
- `environment`: System environment variables

### Special Variables
- `working_dir`: Task working directory
- `install_dir`: Installation directory
- `system`: System-specific information
- `resources`: Resource allocation

## Validation and Error Handling

### Configuration Validation
- Required fields checking
- Type validation
- Version format validation
- Variable name validation

### Template Validation
- Syntax checking
- Variable resolution
- Dependency validation
- Resource validation

### Error Types
1. `TemplateNotFoundError`: Template or file not found
2. `TemplateConfigError`: Invalid configuration
3. `TemplateValidationError`: Validation failure
4. `TemplateVersionError`: Version mismatch
5. `TemplateVariableError`: Variable resolution error
6. `TemplateSyntaxError`: Invalid template syntax

## Best Practices

1. **Template Organization**
   - Group related templates
   - Use consistent naming
   - Version templates appropriately
   - Document dependencies

2. **Variable Management**
   - Use descriptive names
   - Provide defaults where appropriate
   - Document required variables
   - Validate inputs

3. **Error Handling**
   - Validate all inputs
   - Provide clear error messages
   - Include cleanup steps
   - Handle edge cases

4. **Performance**
   - Minimize template complexity
   - Cache rendered templates
   - Optimize variable access
   - Handle large files efficiently 