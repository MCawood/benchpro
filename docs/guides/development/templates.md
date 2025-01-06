# Template Configuration Guide

## Overview

This guide covers the configuration format and options for BenchPRO templates. Templates use YAML configuration files to define their properties, requirements, and behavior.

## Configuration File Structure

### Basic Configuration
```yaml
name: template_name        # Required: Template name
version: 1.0.0            # Required: Semantic version
type: application         # Required: 'application' or 'benchmark'
description: Description  # Optional: Template description
```

### Build Configuration
```yaml
build:
  # Required for application templates
  language: c             # Required: Programming language
  compiler: gcc          # Required: Compiler type
  binary:                # Required: Binary information
    directory: bin       # Required: Output directory
    executable: app      # Required: Executable name
  
  # Optional build settings
  flags:                 # Optional: Build flags
    CFLAGS: "-O3"
    LDFLAGS: "-lm"
  dependencies:          # Optional: Build dependencies
    - make
    - cmake
```

### Source Configuration
```yaml
source:
  # Required for application templates
  files:                 # Required: List of source files
    - src/main.c
    - src/util.c
  
  # Optional source settings
  include_dirs:          # Optional: Include directories
    - include/
  exclude_patterns:      # Optional: Files to exclude
    - "*.o"
    - "*.tmp"
```

### Variable Configuration
```yaml
variables:
  # Optional: Template variables
  COMPILER_FLAGS: "-O3 -march=native"
  MPI_PROCS: 4
  OMP_NUM_THREADS: 8

  # Variable types supported:
  string_var: "value"           # String
  number_var: 42               # Number
  boolean_var: true           # Boolean
  list_var: [1, 2, 3]        # List
  dict_var:                   # Dictionary
    key1: value1
    key2: value2
```

## Field Descriptions

### Required Fields

1. **name**
   - Template identifier
   - Must be unique within type
   - Alphanumeric and underscores
   - Example: `hello_world`

2. **version**
   - Semantic version (MAJOR.MINOR.PATCH)
   - Must follow version format
   - Example: `1.0.0`

3. **type**
   - Template type
   - Must be `application` or `benchmark`
   - Determines required fields

### Optional Fields

1. **description**
   - Human-readable description
   - Markdown formatting supported
   - Example: `Simple hello world application`

2. **tags**
   - List of template tags
   - Used for categorization
   - Example: `[c, mpi, tutorial]`

3. **metadata**
   - Additional template information
   - Arbitrary key-value pairs
   - Example:
     ```yaml
     metadata:
       author: John Doe
       email: john@example.com
       website: https://example.com
     ```

## Variable Naming Rules

1. **Valid Characters**
   - Uppercase letters (A-Z)
   - Numbers (0-9)
   - Underscore (_)
   - Must start with letter

2. **Reserved Names**
   - `build`
   - `source`
   - `variables`
   - `environment`
   - `system`

3. **Best Practices**
   - Use UPPERCASE for environment variables
   - Use lowercase for internal variables
   - Use underscores for spaces
   - Keep names descriptive but concise

## Version Management

### Version Format
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes
- Example: `1.2.3`

### Version Compatibility
- Templates must specify version
- Version updates require validation
- Backward compatibility recommended
- Version history in metadata

## Examples

### Minimal Application Template
```yaml
name: hello_world
version: 1.0.0
type: application
build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: hello
source:
  files:
    - hello.c
```

### Full Application Template
```yaml
name: mpi_benchmark
version: 2.1.0
type: application
description: MPI performance benchmark
tags: [c, mpi, benchmark]

build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: bench
  flags:
    CFLAGS: "-O3 -march=native"
    LDFLAGS: "-lm"
  dependencies:
    - make
    - mpi

source:
  files:
    - src/main.c
    - src/benchmark.c
  include_dirs:
    - include/
  exclude_patterns:
    - "*.o"

variables:
  MPI_PROCS: 4
  PROBLEM_SIZE: "large"
  DEBUG: false

metadata:
  author: Jane Smith
  email: jane@example.com
  version_history:
    - 2.1.0: Added large problem size
    - 2.0.0: Switched to MPI
    - 1.0.0: Initial version
```

### Benchmark Template
```yaml
name: memory_bench
version: 1.0.0
type: benchmark
description: Memory bandwidth benchmark

variables:
  ARRAY_SIZE: "1G"
  ITERATIONS: 100
  THREADS: 4

metadata:
  metrics:
    - bandwidth_read
    - bandwidth_write
    - latency
``` 