# BenchPRO Testing System

BenchPRO uses a comprehensive testing system built on pytest with a centralized test data management architecture. This system provides standardized fixtures, test data, and utilities to ensure consistent, maintainable, and reliable tests across the entire codebase.

## Architecture Overview

The testing system is built around three core principles:

1. **Centralized Test Data**: All test data is defined in a single, authoritative location
2. **Standardized Fixtures**: Reusable pytest fixtures provide consistent test environments
3. **Composition-Based Testing**: Tests can easily combine different data sets and environments

### Directory Structure

```
benchpro/tests/
├── fixtures/
│   ├── __init__.py          # Exports for easy importing
│   ├── test_data.py         # Centralized test data definitions
│   └── setup.py             # Test environment setup utilities
├── conftest.py              # Pytest fixtures and configuration
└── test_*.py                # Individual test modules
```

## Centralized Test Data (`fixtures/test_data.py`)

The heart of the testing system is the centralized test data module, which provides standardized, reusable test data for all tests.

### Standard Application Profiles

Pre-defined application profiles for common testing scenarios:

```python
from benchpro.tests.fixtures.test_data import get_standard_application_profile

# Get a standard test application profile
config = get_standard_application_profile("test_app")
```

Available profiles:
- **`test_app`**: Standard test application with local execution
- **`merge_test`**: Application for testing configuration merging
- **`cli_test`**: Application for testing CLI overrides
- **`test_profile`**: Generic test profile for basic scenarios

### Standard Benchmark Profiles

Pre-defined benchmark profiles for testing benchmark execution:

```python
from benchpro.tests.fixtures.test_data import get_standard_benchmark_profile

# Get a standard test benchmark profile
config = get_standard_benchmark_profile("test_benchmark")
```

Available profiles:
- **`test_benchmark`**: Standard benchmark with complete configuration
- **`orchestrator_test_profile`**: Benchmark for orchestrator testing
- **`factory_test_profile`**: Benchmark for factory testing
- **`golden_path_profile`**: Benchmark for end-to-end testing

### Standard Templates

Pre-defined Jinja2 templates for script generation:

```python
from benchpro.tests.fixtures.test_data import get_standard_template

# Get template content
template_content = get_standard_template("hello_world.j2")
```

Available templates:
- **`hello_world.j2`**: Full-featured template with system info, modules, and execution
- **`vanilla.j2`**: Minimal template for basic command execution
- **`test.j2`**: Simple test template for unit testing
- **`test_app.j2`**: Application-specific build template
- **`test_template.j2`**: SLURM-enabled template with job directives

### Standard Source Files

Pre-defined source code files for testing builds:

```python
from benchpro.tests.fixtures.test_data import get_standard_source_file

# Get source code content
source_code = get_standard_source_file("hello_world.c")
```

Available source files:
- **`hello_world.c`**: Basic C program
- **`test_app.c`**: Test application with argument handling
- **`merge_test.c`**: Simple application for merge testing
- **`cli_test.c`**: Application for CLI testing

### System Configuration

The testing system provides standardized system configuration data that includes all variables expected by templates:

```python
from benchpro.tests.fixtures.test_data import get_standard_system_data

# Get system configuration
system_data = get_standard_system_data()
# Returns: {"name": "test_system", "description": "Test system configuration", ...}
```

## Test Fixtures (`conftest.py`)

BenchPRO provides several standardized pytest fixtures for different testing scenarios.

### Complete Test Environment

The `standardized_test_env` fixture provides a full test environment with all standard data:

```python
def test_complete_workflow(standardized_test_env):
    """Test using the complete standardized environment."""
    # Access pre-created directories
    app_dir = standardized_test_env["inputs_app_dir"]
    source_dir = standardized_test_env["inputs_source_dir"]
    temp_dir = standardized_test_env["temp_dir"]
    
    # All standard profiles, templates, and source files are pre-created
    assert os.path.exists(os.path.join(app_dir, "test_app.yaml"))
    assert os.path.exists(os.path.join(source_dir, "hello_world.c"))
```

### Minimal Test Environment

The `minimal_test_env` fixture provides essential data for fast tests:

```python
def test_basic_functionality(minimal_test_env):
    """Test using minimal environment for speed."""
    # Only essential profiles and templates are created
    # Ideal for unit tests that don't need full data sets
```

### Specialized Test Environments

- **`config_test_env`**: Optimized for configuration management tests
- **`orchestrator_test_env`**: Optimized for orchestrator and workflow tests

## Test Environment Setup (`fixtures/setup.py`)

The setup module provides utilities for creating test environments with specific data sets.

### Environment Setup Functions

```python
from benchpro.tests.fixtures.setup import (
    setup_complete_test_environment,
    setup_minimal_test_environment,
    setup_config_test_environment,
    setup_orchestrator_test_environment
)

# Create complete environment
setup_complete_test_environment(test_env)

# Create minimal environment with specific profiles
setup_minimal_test_environment(test_env)

# Create environment for specific testing needs
setup_config_test_environment(test_env)
```

### Custom Environment Creation

You can create custom environments by specifying exactly what data to include:

```python
from benchpro.tests.fixtures.setup import setup_complete_test_environment

# Create environment with specific profiles and templates
setup_complete_test_environment(
    test_env,
    profile_names=["test_app", "custom_profile"],
    template_names=["hello_world.j2", "custom.j2"],
    source_names=["hello_world.c"]
)
```

## Best Practices

### Writing New Tests

1. **Use Standardized Fixtures**: Always prefer existing fixtures over manual setup
2. **Leverage Standard Data**: Use pre-defined profiles instead of creating inline configurations
3. **Test Isolation**: Each test should be independent and not affect others
4. **Descriptive Names**: Use clear, descriptive test and fixture names

```python
def test_application_build_with_standard_profile(standardized_test_env):
    """Test application building using standardized test data."""
    from benchpro.tests.fixtures.test_data import get_standard_application_profile
    
    # Use standard profile instead of inline configuration
    config = get_standard_application_profile("test_app")
    
    # Test implementation
    # ...
```

### Custom Test Data

When you need custom test data, extend the standard patterns:

```python
def test_custom_scenario(standardized_test_env):
    """Test custom scenario using standard data as base."""
    from benchpro.tests.fixtures.test_data import get_standard_application_profile
    
    # Start with standard data
    config = get_standard_application_profile("test_app")
    
    # Customize for specific test needs
    config.update({
        "custom_field": "custom_value",
        "build": {**config["build"], "flags": "-O3"}
    })
    
    # Test implementation
    # ...
```

### Mock Configuration

When using mocks with the centralized test data, ensure system data is included:

```python
def test_with_mocks(task_factory_with_mocks):
    """Test using mocks with proper system data."""
    factory, mock_config, mock_registry = task_factory_with_mocks
    
    # Get standard data with system configuration
    config = get_standard_application_profile("test_app")
    config["system"] = get_standard_system_data()
    
    # Use in test
    task = factory.create_task(config)
```

## Migration Guide

### From Manual Test Data

**Before (Manual):**
```python
def test_old_pattern(setup_test_env):
    # Manual profile creation
    profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "build": {"source": "test.c", "compiler": "gcc"},
        # ... lots of boilerplate
    }
    
    # Manual file creation
    with open(os.path.join(test_env["dir"], "profile.yaml"), "w") as f:
        yaml.dump(profile, f)
```

**After (Standardized):**
```python
def test_new_pattern(standardized_test_env):
    # Use standard profile - all data pre-created
    from benchpro.tests.fixtures.test_data import get_standard_application_profile
    
    config = get_standard_application_profile("test_app")
    # Profile and files already exist in test environment
```

### From Custom Fixtures

**Before (Custom):**
```python
@pytest.fixture
def custom_test_env():
    temp_dir = tempfile.mkdtemp()
    # Manual directory and file creation
    # ... lots of setup code
    yield {"temp_dir": temp_dir}
    shutil.rmtree(temp_dir)
```

**After (Standardized):**
```python
def test_functionality(standardized_test_env):
    # Use standardized fixture - no custom setup needed
    # All directories and files pre-created
```

## Common Patterns

### Testing Configuration Management

```python
def test_config_merging(config_test_env):
    """Test configuration merging with standard data."""
    from benchpro.config.config_manager import ConfigManager
    from benchpro.utils.user_dir import get_user_dir_manager
    
    user_dir_manager = get_user_dir_manager(base_dir=config_test_env["temp_dir"])
    config_manager = ConfigManager(user_dir_manager=user_dir_manager)
    
    # Standard profiles are already available
    merged_config = config_manager.merge_configs("test_app", {"build": {"flags": "-O3"}})
    
    assert merged_config["build"]["flags"] == "-O3"
```

### Testing Task Orchestration

```python
def test_task_orchestration(orchestrator_test_env, monkeypatch):
    """Test task orchestration with standard data."""
    # Mock execution to avoid actual job submission
    def mock_execute(self, script_path, workspace=None):
        return True, "test_job_id"
    monkeypatch.setattr("benchpro.executor.components.execution.LocalExecutionComponent.execute", mock_execute)
    
    from benchpro.executor.task_orchestrator import TaskOrchestrator
    from benchpro.config.config_manager import ConfigManager
    from benchpro.utils.user_dir import get_user_dir_manager
    
    user_dir_manager = get_user_dir_manager(base_dir=orchestrator_test_env["temp_dir"])
    config_manager = ConfigManager(user_dir_manager=user_dir_manager)
    orchestrator = TaskOrchestrator(config_manager)
    
    # Use standard profile that's already available
    success, job_id, script_path = orchestrator.execute("test_app", {}, dry_run=False)
    
    assert success is True
    assert job_id == "test_job_id"
    assert os.path.exists(script_path)
```

### Testing Template Generation

```python
def test_template_generation(standardized_test_env):
    """Test template generation with standard data."""
    from benchpro.executor.task_factory import TaskFactory
    from benchpro.tests.fixtures.test_data import get_standard_application_profile, get_standard_system_data
    
    # Create task factory
    factory = TaskFactory(mock_config_manager, mock_registry_manager)
    
    # Use standard profile with system data
    config = get_standard_application_profile("test_app")
    config["system"] = get_standard_system_data()
    
    task = factory.create_task(config)
    
    # Standard templates are available in test environment
    template_path = os.path.join(standardized_test_env["inputs_app_dir"], "hello_world.j2")
    script_path = "/tmp/test_script.sh"
    
    # Generate script
    result_path = task.generate_script(template_path, script_path)
    assert os.path.exists(result_path)
```

## Troubleshooting

### Common Issues

**Template Rendering Errors:**
- Ensure system data is included: `config["system"] = get_standard_system_data()`
- Check that required variables are defined in the configuration

**Profile Not Found:**
- Verify the profile name exists in `STANDARD_APPLICATION_PROFILES` or `STANDARD_BENCHMARK_PROFILES`
- Use `get_all_standard_profiles()` to see available profiles

**File Not Found Errors:**
- Ensure you're using the correct fixture (`standardized_test_env` vs `minimal_test_env`)
- Check that the required files are included in the environment setup

**Mock Configuration Issues:**
- When using mocked dependencies, ensure configuration includes all required fields
- Include system data for template rendering: `config["system"] = get_standard_system_data()`

### Debug Information

To see what data is available in your test environment:

```python
def test_debug_environment(standardized_test_env):
    """Debug what's available in the test environment."""
    print("Test environment structure:")
    for key, value in standardized_test_env.items():
        print(f"  {key}: {value}")
    
    # List available profiles
    from benchpro.tests.fixtures.test_data import get_all_standard_profiles
    profiles = get_all_standard_profiles()
    print("Available profiles:", list(profiles.keys()))
```

## Contributing to the Testing System

### Adding New Standard Data

To add new standard profiles, templates, or source files:

1. Add the definition to the appropriate dictionary in `benchpro/tests/fixtures/test_data.py`
2. Update the setup functions in `benchpro/tests/fixtures/setup.py` if needed
3. Add documentation to this file
4. Write tests that use the new data

### Adding New Fixtures

To add new specialized fixtures:

1. Add the fixture function to `benchpro/tests/conftest.py`
2. Use the existing setup utilities from `benchpro/tests/fixtures/setup.py`
3. Document the fixture and its intended use case
4. Provide usage examples

The centralized testing system is designed to be extensible and maintainable. When adding new test data or fixtures, follow the established patterns to ensure consistency and ease of use for all developers. 