# Writing Tests in BenchPRO

This guide explains how to write tests in BenchPRO following established conventions and best practices. Following these guidelines ensures consistent, maintainable tests that integrate well with the existing test suite.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Available Fixtures](#available-fixtures)
3. [Test Data Structure](#test-data-structure)
4. [Common Patterns](#common-patterns)
5. [What to Avoid](#what-to-avoid)
6. [Examples](#examples)
7. [Testing Different Components](#testing-different-components)

## Core Principles

### 1. **Use Existing Fixtures First**
Before creating any custom setup, check if an existing fixture meets your needs. The centralized fixtures provide:
- Consistent test environments
- Standardized test data
- Proper isolation from user directories
- Proven reliability

### 2. **Test Isolation**
Every test must be completely isolated from:
- The user's actual `~/.benchpro` directory
- Other tests running concurrently
- System state and configuration

### 3. **Standardized Test Data**
Use the centralized test data definitions instead of creating ad-hoc test configurations.

### 4. **Clear Test Intent**
Test names and structure should clearly indicate what functionality is being tested.

## Available Fixtures

### Primary Test Environment Fixtures

#### `config_test_env`
**Use for**: Configuration-related tests
```python
def test_config_functionality(config_test_env):
    config_manager = ConfigManager()
    # Test environment is automatically set up with:
    # - Standard default.yaml and system configs
    # - Standard profiles: test_app, merge_test, cli_test, test_profile
    # - Proper directory structure
```

**Provides**:
- Standard configuration files (default.yaml, system configs)
- Test profiles for configuration testing
- Isolated test directories
- Automatic cleanup

#### `standardized_test_env`
**Use for**: Comprehensive tests needing full test data
```python
def test_complex_functionality(standardized_test_env):
    # Complete test environment with all standard profiles, templates, sources
```

**Provides**:
- All standard application and benchmark profiles
- All standard templates (hello_world.j2, vanilla.j2, etc.)
- All standard source files
- Complete directory structure

#### `minimal_test_env`
**Use for**: Simple tests needing minimal setup
```python
def test_basic_functionality(minimal_test_env):
    # Minimal environment with essential test data only
```

**Provides**:
- Essential profiles only (test_app, test_benchmark)
- Essential templates and source files
- Faster setup for simple tests

#### `orchestrator_test_env`
**Use for**: TaskOrchestrator and end-to-end tests
```python
def test_orchestrator_functionality(orchestrator_test_env):
    orchestrator = TaskOrchestrator()
    # Environment set up specifically for orchestrator testing
```

### Component-Specific Fixtures

#### `temp_registry`
**Use for**: Registry-related tests
```python
def test_registry_operations(temp_registry):
    # Isolated registry for testing
```

#### `temp_workspace_manager`
**Use for**: Workspace management tests
```python
def test_workspace_creation(temp_workspace_manager):
    # Automatic workspace cleanup
```

## Test Data Structure

### Standard Test Profiles

The test data is centralized in `benchpro/tests/fixtures/test_data.py`:

#### Application Profiles
- `test_app`: Standard test application
- `merge_test`: For configuration merging tests
- `cli_test`: For CLI override tests
- `test_profile`: Generic test profile

#### Benchmark Profiles  
- `test_benchmark`: Standard test benchmark
- `orchestrator_test_profile`: For orchestrator tests
- `factory_test_profile`: For factory tests

#### Templates
- `hello_world.j2`: Standard build/run template
- `vanilla.j2`: Minimal template
- `test.j2`: Test-specific template

### Directory Structure
When using fixtures, the test environment provides:
```
temp_dir/
├── config/
│   ├── default.yaml
│   └── system/
│       └── default.yaml
├── inputs/
│   ├── application/
│   │   ├── test_app.yaml
│   │   ├── merge_test.yaml
│   │   └── *.j2 templates
│   ├── benchmark/
│   │   ├── test_benchmark.yaml
│   │   └── *.j2 templates
│   └── source/
│       ├── hello_world.c
│       └── test_app.c
├── outputs/
│   ├── application/
│   └── benchmark/
└── registry/
```

## Common Patterns

### 1. Configuration Testing
```python
def test_config_loading(config_test_env):
    """Test configuration loading functionality."""
    config_manager = ConfigManager()
    
    # The config_test_env fixture automatically sets up user_dir_manager
    config = config_manager.get_complete_config("test_app")
    
    assert config["task_type"] == "application"
    assert config["name"] == "test_app"
```

### 2. Component Testing with Mocks
```python
from unittest.mock import Mock, patch

def test_component_with_mocks(config_test_env):
    """Test component behavior with mocked dependencies."""
    with patch('benchpro.some_module.external_dependency') as mock_dep:
        mock_dep.return_value = "mocked_result"
        
        component = SomeComponent()
        result = component.method_using_dependency()
        
        assert result == "expected_result"
        mock_dep.assert_called_once()
```

### 3. End-to-End Testing
```python
def test_end_to_end_workflow(orchestrator_test_env):
    """Test complete workflow from profile to execution."""
    orchestrator = TaskOrchestrator()
    
    success, job_id, script_path = orchestrator.execute("test_app", dry_run=True)
    
    assert success
    assert script_path.endswith(".sh")
```

### 4. Error Handling Tests
```python
def test_error_conditions(config_test_env):
    """Test proper error handling."""
    config_manager = ConfigManager()
    
    with pytest.raises(FileNotFoundError, match="Profile not found"):
        config_manager.get_complete_config("nonexistent_profile")
```

## What to Avoid

### ❌ **DON'T: Create Custom Fixtures for Standard Scenarios**

**Real Example of What NOT to Do:**
```python
# DON'T DO THIS - This was the actual mistake made when adding parameter tracking tests
@pytest.fixture
def config_test_env():
    """Create a test environment with configuration files."""
    temp_dir = tempfile.mkdtemp()
    
    # Manual config directory setup
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir)
    
    # Manual default config creation
    default_config = {
        "execution": {"type": "local"},
        "job": {"scheduler": "slurm", "time_limit": "01:00:00"}
    }
    with open(os.path.join(config_dir, "default.yaml"), 'w') as f:
        yaml.dump(default_config, f)
    
    # Manual profile creation
    profile_dir = os.path.join(temp_dir, "profiles", "application")
    os.makedirs(profile_dir)
    test_profile = {"task_type": "application", "name": "test_app"}
    with open(os.path.join(profile_dir, "test_app.yaml"), 'w') as f:
        yaml.dump(test_profile, f)
    
    # Using manual filesystem setup
    test_fs = create_temp_fs(temp_dir=temp_dir)
    config_manager = ConfigManager(
        config_dir=config_dir,
        profile_dir=profile_dir,
        file_system=test_fs
    )
    
    return {"temp_dir": temp_dir, "config_dir": config_dir}
```

**Why This is Wrong:**
1. **Duplication**: This recreates setup that already exists in `config_test_env` fixture
2. **Inconsistency**: Manual config differs from standardized test data
3. **Maintenance**: Any changes to test data structure require updating multiple places
4. **Isolation Issues**: Manual setup may not follow established isolation patterns

**✅ DO: Use existing fixtures**
```python
def test_config_tracking_functionality(config_test_env):
    """Test new parameter tracking - CORRECT approach using existing fixture."""
    # The config_test_env fixture automatically provides:
    # - Isolated test environment 
    # - Standard test_app profile
    # - Proper user_dir_manager setup
    # - Automatic cleanup
    
    config_manager = ConfigManager()  # Uses fixture-configured environment
    report = config_manager.get_complete_config_report("test_app")
    
    assert isinstance(report, ConfigReport)
    assert report.profile_name == "test_app"
```

**Key Lesson from Parameter Tracking Implementation:**
When adding the parameter tracking feature, the initial test implementation made the mistake above - creating custom fixtures instead of using the existing `config_test_env`. This led to:
- Test failures due to profile not being found (manual setup was incomplete)
- Inconsistent test data compared to other config tests
- Wasted development time debugging setup issues instead of testing functionality

**Always check `conftest.py` first before writing ANY test setup code.**

### ❌ **DON'T: Manual Directory Setup**
```python
# DON'T DO THIS
def test_config_loading():
    temp_dir = tempfile.mkdtemp()
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir)
    # ... manual file creation
```

**✅ DO: Use fixtures that handle setup**
```python
def test_config_loading(config_test_env):
    # Directory structure already set up
```

### ❌ **DON'T: Create Inconsistent Test Data**
```python
# DON'T DO THIS
def test_with_custom_profile():
    profile = {
        "task_type": "application",
        "name": "my_test_app",
        # ... custom structure that differs from standards
    }
```

**✅ DO: Use standardized test data**
```python
def test_with_standard_profile(config_test_env):
    # Use test_app profile which follows standard structure
    config_manager = ConfigManager()
    config = config_manager.get_complete_config("test_app")
```

### ❌ **DON'T: Ignore Test Isolation**
```python
# DON'T DO THIS - modifies global state
def test_that_modifies_global_state():
    os.environ["BENCHPRO_CONFIG"] = "/some/path"
    # Test that could affect other tests
```

**✅ DO: Use proper mocking and isolation**
```python
def test_with_proper_isolation(config_test_env):
    with patch.dict(os.environ, {"BENCHPRO_CONFIG": "/some/path"}):
        # Changes are isolated to this test
```

### ❌ **DON'T: Hardcode File Paths**
```python
# DON'T DO THIS
def test_with_hardcoded_paths():
    config_path = "/tmp/my_test_config.yaml"
    # Hardcoded paths can cause conflicts
```

**✅ DO: Use fixture-provided paths**
```python
def test_with_fixture_paths(config_test_env):
    # Use paths from the test environment
    config_dir = config_test_env["config_dir"]
```

### ❌ **DON'T: Skip Cleanup**
```python
# DON'T DO THIS
def test_that_leaves_files():
    temp_file = "/tmp/test_file"
    with open(temp_file, "w") as f:
        f.write("test data")
    # File is never cleaned up
```

**✅ DO: Use fixtures with automatic cleanup**
```python
def test_with_automatic_cleanup(config_test_env):
    # Fixtures handle cleanup automatically
```

## Examples

### Configuration System Tests

```python
class TestConfigurationSystem:
    """Example of properly structured configuration tests."""
    
    def test_default_config_loading(self, config_test_env):
        """Test loading default configuration."""
        config_manager = ConfigManager()
        default_config = config_manager.load_default_config()
        
        assert "task_type" in default_config
        assert "job" in default_config
    
    def test_profile_config_loading(self, config_test_env):
        """Test loading profile configuration."""
        config_manager = ConfigManager()
        profile_config = config_manager.get_complete_config("test_app")
        
        assert profile_config["task_type"] == "application"
        assert profile_config["name"] == "test_app"
    
    def test_config_merging(self, config_test_env):
        """Test configuration merging with CLI overrides."""
        config_manager = ConfigManager()
        cli_overrides = {"version": "2.0"}
        
        config = config_manager.get_complete_config("test_app", cli_overrides)
        
        assert config["version"] == "2.0"
        assert config["name"] == "test_app"  # From profile
```

### Component Tests with Dependencies

```python
class TestTaskOrchestrator:
    """Example of component testing with proper dependency handling."""
    
    def test_task_creation(self, orchestrator_test_env):
        """Test task creation through orchestrator."""
        orchestrator = TaskOrchestrator()
        
        success, job_id, script_path = orchestrator.execute(
            "test_app", 
            cli_overrides={"execution": {"type": "local"}},
            dry_run=True
        )
        
        assert success
        assert script_path
        assert os.path.exists(script_path)
    
    @patch('benchpro.executor.scheduler.SlurmExecutionComponent')
    def test_slurm_integration(self, mock_slurm, orchestrator_test_env):
        """Test SLURM integration with mocked scheduler."""
        mock_slurm.return_value.submit.return_value = (True, "12345")
        
        orchestrator = TaskOrchestrator()
        success, job_id, script_path = orchestrator.execute(
            "test_app",
            cli_overrides={"execution": {"type": "sched"}}
        )
        
        assert success
        assert job_id == "12345"
```

### Error Handling Tests

```python
class TestErrorHandling:
    """Example of proper error handling tests."""
    
    def test_missing_profile_error(self, config_test_env):
        """Test error when profile doesn't exist."""
        config_manager = ConfigManager()
        
        with pytest.raises(FileNotFoundError, match="Profile not found"):
            config_manager.get_complete_config("nonexistent_profile")
    
    def test_invalid_config_error(self, config_test_env):
        """Test error handling for invalid configuration."""
        config_manager = ConfigManager()
        
        # Create invalid override
        invalid_overrides = {"job": {"nodes": "invalid_number"}}
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager.get_complete_config("test_app", invalid_overrides)
```

## Testing Different Components

### Configuration System
- Use `config_test_env` fixture
- Test with standard profiles: `test_app`, `merge_test`, `cli_test`
- Use `ConfigManager()` directly (fixture sets up user_dir_manager)

### Task Orchestration
- Use `orchestrator_test_env` fixture
- Test with `TaskOrchestrator()` 
- Use dry_run=True for most tests

### Registry Operations
- Use `temp_registry` fixture
- Test with `RegistryManager` from fixture

### Workspace Management
- Use `temp_workspace_manager` fixture
- Automatic cleanup of created workspaces

### CLI Testing
- Use `standardized_test_env` for full CLI tests
- Mock subprocess calls for scheduler interactions
- Test both success and error scenarios

## Best Practices Summary

1. **Always use existing fixtures first** - check `conftest.py` before creating custom setup
2. **Follow established patterns** - look at existing tests in the same area
3. **Use standardized test data** - from `benchpro/tests/fixtures/test_data.py`
4. **Ensure test isolation** - tests should never affect each other
5. **Test error conditions** - not just happy paths
6. **Use descriptive test names** - clearly indicate what's being tested
7. **Keep tests focused** - one concept per test method
8. **Use proper mocking** - for external dependencies and slow operations
9. **Verify cleanup** - fixtures should handle this automatically

## Getting Help

- **Check existing tests**: Look in `benchpro/tests/` for similar functionality
- **Review fixtures**: See `benchpro/tests/conftest.py` for available fixtures
- **Examine test data**: Check `benchpro/tests/fixtures/test_data.py` for standard data
- **Follow patterns**: Use the same structure as existing tests

Remember: **If you find yourself manually creating test environments or data that seems like it should be standard, check if a fixture already exists or should be created for reuse.**

## Quick Reference Checklist

Before writing any test, ask yourself:

### ✅ Pre-Test Checklist
1. **What am I testing?** (Configuration? Orchestration? CLI? Registry?)
2. **Does a fixture exist for this?** (Check `conftest.py` for available fixtures)
3. **What test data do I need?** (Check `test_data.py` for standard profiles)
4. **Am I testing in isolation?** (No user directory interaction, no global state changes)

### 🔍 Fixture Selection Guide
- **Configuration testing** → `config_test_env`
- **Full integration testing** → `standardized_test_env`  
- **Simple component testing** → `minimal_test_env`
- **Orchestrator/end-to-end** → `orchestrator_test_env`
- **Registry operations** → `temp_registry`
- **Workspace management** → `temp_workspace_manager`

### 🚫 Red Flags (Stop and Reconsider)
- Creating `@pytest.fixture` for standard scenarios
- Using `tempfile.mkdtemp()` directly
- Creating config files manually (`default.yaml`, profiles)
- Using `TempFileSystem` or `create_temp_fs` for standard tests
- Hardcoding file paths or directory structures
- Setting up test data that differs from standards

### ✅ Green Lights (Good Practices)
- Using existing fixtures from `conftest.py`
- Testing with standard profiles (`test_app`, `test_benchmark`)
- Following existing test patterns in the same module
- Using proper mocking for external dependencies
- Clear, descriptive test names
- One concept per test method

**When in doubt: Look at existing tests in the same area for patterns to follow.** 