# Template Development Guide

## Overview

This guide covers the process of creating, testing, and maintaining templates in BenchPRO. Templates are the core mechanism for defining how applications are built and benchmarks are run.

## Creating Templates

### 1. Template Directory Structure
```
my_template/
├── config.yaml          # Template configuration
├── build.j2            # Build script template
├── run.j2             # Run script template
└── README.md          # Template documentation
```

### 2. Basic Template Creation

1. Create template directory:
```bash
mkdir -p templates/applications/my_template
cd templates/applications/my_template
```

2. Create configuration file:
```yaml
# config.yaml
name: my_template
version: 1.0.0
type: application
description: My template description

build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: my_app
```

3. Create build template:
```bash
# build.j2
#!/bin/bash
#
# Build script for {{ name }} v{{ version }}
#
cd {{ working_dir }}

# Set up environment
export CC="{{ build.compiler }}"
export CFLAGS="{{ variables.CFLAGS|default('-O2') }}"

# Build application
$CC $CFLAGS -o {{ build.binary.executable }} {{ source.files|join(' ') }}

# Verify build
if [ ! -f {{ build.binary.executable }} ]; then
    echo "Error: Build failed"
    exit 1
fi
```

4. Create run template:
```bash
# run.j2
#!/bin/bash
#
# Run script for {{ name }} v{{ version }}
#
cd {{ working_dir }}

# Set up environment
export OMP_NUM_THREADS={{ variables.THREADS|default(1) }}

# Run application
./{{ build.binary.executable }} {{ variables.ARGS|default('') }}
```

## Template Features

### 1. Variable Substitution

```bash
# Simple substitution
echo "Running {{ name }} version {{ version }}"

# Nested attributes
compiler="{{ build.compiler }}"
flags="{{ build.flags.CFLAGS }}"

# Default values
threads="{{ variables.THREADS|default(1) }}"
```

### 2. Conditional Logic

```bash
# If statement
{% if build.language == "c" %}
$CC $CFLAGS -o $OUTPUT $SOURCES
{% elif build.language == "cpp" %}
$CXX $CXXFLAGS -o $OUTPUT $SOURCES
{% endif %}

# For loop
{% for file in source.files %}
echo "Compiling {{ file }}..."
{% endfor %}
```

### 3. Error Handling

```bash
# Check required variables
{% if not variables.INPUT_FILE %}
echo "Error: INPUT_FILE not specified"
exit 1
{% endif %}

# Validate paths
if [ ! -d "{{ working_dir }}" ]; then
    echo "Error: Working directory not found"
    exit 1
fi
```

### 4. Resource Management

```bash
# Memory limits
{% if resources.memory_gb %}
export MEM_LIMIT="{{ resources.memory_gb }}G"
{% endif %}

# CPU allocation
{% if resources.cpu_cores %}
export OMP_NUM_THREADS="{{ resources.cpu_cores }}"
{% endif %}
```

## Testing Templates

### 1. Unit Tests

Create test file `tests/unit/templates/test_my_template.py`:
```python
def test_template_config():
    """Test template configuration loading."""
    config = TemplateConfig.from_file("my_template/config.yaml")
    assert config.name == "my_template"
    assert config.version == "1.0.0"
    assert config.type == "application"

def test_template_rendering():
    """Test template rendering with variables."""
    template = Template.load("my_template/build.j2")
    context = {
        "name": "test",
        "version": "1.0.0",
        "working_dir": "/tmp/test",
        "build": {
            "compiler": "gcc",
            "binary": {"executable": "test"}
        }
    }
    result = template.render(context)
    assert "gcc" in result
    assert "/tmp/test" in result
```

### 2. Integration Tests

Create test file `tests/integration/templates/test_my_template.py`:
```python
@pytest.mark.asyncio
async def test_template_execution():
    """Test full template execution."""
    # Create task
    task = Task.create("test", "my_template")
    
    # Set variables
    task.set_variable("THREADS", 4)
    
    # Run task
    result = await task.run()
    assert result.exit_code == 0
    assert result.output contains "Success"
```

### 3. Test Cases

1. **Basic Functionality**
   - Default configuration
   - Minimal variables
   - Standard execution

2. **Variable Handling**
   - Missing variables
   - Invalid values
   - Type conversion

3. **Error Conditions**
   - Resource limits
   - Missing files
   - Invalid paths

4. **Performance**
   - Large files
   - Many variables
   - Complex logic

## Template Maintenance

### 1. Version Updates

1. Update version in `config.yaml`:
```yaml
version: 1.1.0  # From 1.0.0
```

2. Document changes:
```yaml
metadata:
  version_history:
    - 1.1.0: Added GPU support
    - 1.0.0: Initial version
```

3. Update tests:
```python
def test_gpu_support():
    """Test new GPU features."""
    config = TemplateConfig.from_file("config.yaml")
    assert config.version == "1.1.0"
    assert "gpu" in config.resources
```

### 2. Compatibility

1. Check backward compatibility:
```python
def test_backward_compatibility():
    """Test compatibility with old task configs."""
    old_config = {
        "version": "1.0.0",
        "variables": {"THREADS": 4}
    }
    task = Task.from_config(old_config)
    assert task.is_valid()
```

2. Migration support:
```python
def migrate_config(old_config):
    """Migrate configuration to new version."""
    if old_config["version"] == "1.0.0":
        old_config["version"] = "1.1.0"
        old_config["resources"] = {"gpu": False}
    return old_config
```

## Best Practices

### 1. Template Design

1. **Modularity**
   - Split complex templates
   - Use include statements
   - Share common code

2. **Documentation**
   - Describe purpose
   - List requirements
   - Provide examples

3. **Validation**
   - Check inputs
   - Validate paths
   - Handle errors

### 2. Testing Strategy

1. **Test Coverage**
   - Unit tests for logic
   - Integration tests for workflow
   - Performance tests for scaling

2. **Test Cases**
   - Common scenarios
   - Edge cases
   - Error conditions

3. **Continuous Testing**
   - Automated tests
   - Regular validation
   - Performance monitoring

### 3. Maintenance

1. **Version Control**
   - Semantic versioning
   - Change documentation
   - Migration support

2. **Updates**
   - Regular review
   - Security patches
   - Performance improvements

3. **Support**
   - User documentation
   - Example configurations
   - Troubleshooting guides 