# Testing Documentation

This section contains comprehensive documentation for BenchPRO's testing infrastructure and best practices.

## Overview

BenchPRO employs a sophisticated testing architecture designed to provide reliable, maintainable, and comprehensive test coverage across all components. The testing system emphasizes:

- **Centralized Test Data Management**: Standardized, reusable test data and fixtures
- **Realistic Mocking**: Comprehensive simulation of external dependencies
- **Integration Testing**: End-to-end testing of complete workflows
- **Best Practices**: Established patterns and conventions for test development

## Documentation Contents

### [Testing System](testing.md)
Comprehensive guide to BenchPRO's centralized testing infrastructure:
- **Centralized Test Data**: Standardized profiles, templates, and source files
- **Pytest Fixtures**: Reusable test environments and utilities
- **Test Patterns**: Common patterns for different types of tests
- **Migration Guide**: How to update existing tests to use the new system
- **Troubleshooting**: Common issues and solutions

### [SLURM Testing Guide](slurm-testing-guide.md)
Specialized guide for testing SLURM functionality:
- **Mock SLURM System**: Comprehensive simulation of SLURM behavior
- **Testing Patterns**: Component, integration, and error handling tests
- **Fixture Usage**: How to use SLURM-specific fixtures effectively
- **Implementation Issues**: Documented fixes and resolutions
- **Best Practices**: Recommended approaches for SLURM testing

## Key Features

### Centralized Test Data
All test data is defined in a single, authoritative location (`benchpro/tests/fixtures/test_data.py`), providing:
- **Standard Application Profiles**: Pre-configured application settings
- **Standard Benchmark Profiles**: Pre-configured benchmark definitions
- **Standard Templates**: Reusable Jinja2 templates for script generation
- **Standard Source Files**: Sample source code for build testing
- **System Configuration**: Standardized system data for template rendering

### Realistic Mocking
Comprehensive mock systems that accurately simulate real dependencies:
- **Mock SLURM System**: Full SLURM command simulation with job lifecycle
- **Mock File Systems**: Temporary directories with realistic structure
- **Mock Subprocess**: Controlled execution environment

### Test Environment Fixtures
Multiple pytest fixtures for different testing scenarios:
- **`standardized_test_env`**: Complete test environment with all data
- **`minimal_test_env`**: Lightweight environment for fast unit tests
- **`slurm_patched`**: Automatic SLURM command patching
- **`slurm_with_standardized_env`**: Combined SLURM and standardized environment

## Getting Started

### For New Tests
Use the standardized fixtures and test data:

```python
def test_application_build(standardized_test_env):
    """Test using standardized test environment."""
    from benchpro.tests.fixtures.test_data import get_standard_application_profile
    
    config = get_standard_application_profile("test_app")
    # Test logic here
```

### For SLURM Tests
Use the SLURM-specific fixtures:

```python
def test_slurm_submission(slurm_patched):
    """Test SLURM job submission."""
    from benchpro.executor.scheduler import SlurmScheduler
    
    scheduler = SlurmScheduler()
    job_id = scheduler.submit_job("test_script.sh")
    # Test logic here
```

### For Integration Tests
Combine multiple fixtures for comprehensive testing:

```python
def test_end_to_end_workflow(slurm_with_standardized_env):
    """Test complete workflow with SLURM integration."""
    # Access both test data and SLURM mocking
    mock_slurm = slurm_with_standardized_env["mock_slurm"]
    inputs_dir = slurm_with_standardized_env["inputs_app_dir"]
    # Test logic here
```

## Contributing to Testing

When adding new tests or extending the testing system:

1. **Use Existing Fixtures**: Prefer standardized fixtures over custom setup
2. **Add Standard Data**: Extend centralized test data rather than creating inline data
3. **Document Issues**: Add resolution details to the appropriate guide
4. **Follow Patterns**: Use established testing patterns and conventions
5. **Test Comprehensively**: Include unit, integration, and error handling tests

## Benefits

The centralized testing system provides:

- **Faster Development**: Reusable fixtures and data reduce setup time
- **Better Coverage**: Comprehensive mocking enables testing of edge cases
- **Maintainable Tests**: Centralized data management reduces duplication
- **Consistent Quality**: Standardized patterns ensure test reliability
- **Easy Debugging**: Clear documentation and realistic mocking aid troubleshooting

For detailed information on specific testing topics, refer to the individual guides above. 