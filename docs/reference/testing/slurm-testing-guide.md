# SLURM Testing Guide

## Overview

Testing SLURM functionality in BenchPRO has been significantly improved with a comprehensive mock SLURM system that allows thorough validation of SLURM integration without requiring actual SLURM installation. This guide explains the testing strategy, available tools, and best practices.

## Problem Statement

**Previous Challenges:**
- Scattered, inconsistent mocking across test files
- Limited test coverage of SLURM edge cases
- Maintenance burden when SLURM interfaces change
- No integration testing of complete job lifecycles
- Tests only covered happy-path scenarios

**Solution:**
A centralized, realistic mock SLURM system that provides:
- Comprehensive simulation of SLURM commands (`sbatch`, `squeue`, `sacct`, `scancel`)
- Realistic job lifecycle progression (PENDING → RUNNING → COMPLETED/FAILED)
- Error scenario simulation (network failures, job failures, etc.)
- Integration with existing centralized test fixtures
- Easy-to-use testing utilities and helpers

## Architecture

### Core Components

1. **MockSlurmSystem**: Core mock that simulates SLURM behavior
2. **MockSlurmCommands**: Subprocess patches for SLURM command interception
3. **SlurmTestHelper**: Convenience utilities for common testing scenarios
4. **Centralized Fixtures**: Integration with existing test infrastructure

### Key Features

- **Realistic Job Lifecycle**: Jobs automatically progress through states with configurable timing
- **Command History Tracking**: Monitor which SLURM commands were called and when
- **Error Injection**: Simulate various failure scenarios for robust error handling tests
- **SBATCH Directive Parsing**: Parse and validate `#SBATCH` directives from scripts
- **Integration Ready**: Works seamlessly with existing BenchPRO components

## Quick Start

### Basic Usage

```python
def test_slurm_job_submission(slurm_patched):
    """Test basic SLURM job submission."""
    from benchpro.executor.scheduler import SlurmScheduler
    from benchpro.tests.fixtures import create_minimal_slurm_script
    
    # Create a test script
    script_path = create_minimal_slurm_script("test_job")
    
    try:
        # Submit job
        scheduler = SlurmScheduler()
        job_id = scheduler.submit_job(script_path)
        
        # Verify submission
        assert job_id.isdigit()
        
        # Check job exists in mock system
        job = slurm_patched.get_job(job_id)
        assert job is not None
        assert job.job_name == "test_job"
        
    finally:
        os.unlink(script_path)
```

### Using Test Helpers

```python
def test_job_lifecycle_with_helper(slurm_patched):
    """Test complete job lifecycle using helper utilities."""
    from benchpro.tests.fixtures import SlurmTestHelper
    from benchpro.tests.fixtures.mock_slurm import JobState
    
    helper = SlurmTestHelper(slurm_patched)
    
    # Submit job
    job_id = helper.submit_test_job()
    
    # Wait for completion
    assert helper.wait_for_completion(job_id, timeout=2.0)
    
    # Verify final state
    helper.assert_job_reached_state(job_id, JobState.COMPLETED)
    
    # Check command history
    helper.assert_command_called("sbatch", times=1)
```

## Available Fixtures

### Core Fixtures

#### `mock_slurm_basic`
Basic mock SLURM system for simple tests.

```python
def test_with_basic_mock(mock_slurm_basic):
    """Simple test with basic mock SLURM."""
    # Use mock_slurm_basic for manual control
    job_id = mock_slurm_basic.submit_job("test_script.sh")
```

#### `slurm_patched`
Automatically patches subprocess calls for SLURM commands.

```python
def test_with_automatic_patching(slurm_patched):
    """Test with automatic subprocess patching."""
    # All SLURM subprocess calls automatically use mock system
    from benchpro.executor.scheduler import SlurmScheduler
    scheduler = SlurmScheduler()
    job_id = scheduler.submit_job("test_script.sh")
```

#### `slurm_with_standardized_env`
Complete testing environment with standardized test data and mock SLURM.

```python
def test_integration_scenario(slurm_with_standardized_env):
    """Test with full standardized environment."""
    # Access both test data and mock SLURM
    mock_slurm = slurm_with_standardized_env["mock_slurm"]
    templates_dir = slurm_with_standardized_env["inputs_app_dir"]
    
    # Use standardized templates and profiles
    from benchpro.tests.fixtures import get_standard_application_profile
    config = get_standard_application_profile("test_app")
```

### Specialized Fixtures

#### `mock_slurm_system_manual`
Mock system with manual job progression for precise control.

```python
def test_precise_state_control(mock_slurm_system_manual):
    """Test with manual control over job state progression."""
    job_id = mock_slurm_system_manual.submit_job("test_script.sh")
    
    # Manually control job state
    mock_slurm_system_manual.set_job_state(job_id, JobState.RUNNING)
    mock_slurm_system_manual.set_job_state(job_id, JobState.FAILED)
```

## Testing Patterns

### 1. Component Testing

Test individual SLURM components in isolation:

```python
class TestSlurmScheduler:
    """Test SlurmScheduler class."""
    
    def test_submit_job(self, slurm_patched):
        """Test job submission."""
        scheduler = SlurmScheduler()
        job_id = scheduler.submit_job("test_script.sh")
        assert job_id.isdigit()
    
    def test_check_status(self, slurm_patched):
        """Test status checking."""
        scheduler = SlurmScheduler()
        job_id = scheduler.submit_job("test_script.sh")
        
        # Wait for job to complete
        slurm_patched.wait_for_job_state(job_id, JobState.COMPLETED)
        
        status = scheduler.check_status(job_id)
        assert status == "COMPLETED"
```

### 2. Integration Testing

Test complete workflows:

```python
def test_end_to_end_workflow(slurm_with_standardized_env):
    """Test complete SLURM workflow."""
    from benchpro.templates.script_generators import SlurmScriptGenerator
    from benchpro.executor.components.execution import SlurmExecutionComponent
    
    # Generate script
    generator = SlurmScriptGenerator()
    script_content = generator.generate_script(template_path, variables)
    
    # Submit script
    component = SlurmExecutionComponent()
    success, job_id = component.execute(script_path)
    
    # Verify completion
    mock_slurm = slurm_with_standardized_env["mock_slurm"]
    mock_slurm.wait_for_job_state(job_id, JobState.COMPLETED)
```

### 3. Error Handling Testing

Test various failure scenarios:

```python
def test_error_scenarios(slurm_patched):
    """Test error handling."""
    from benchpro.tests.fixtures import SlurmTestHelper
    
    helper = SlurmTestHelper(slurm_patched)
    
    # Test network failure
    helper.simulate_network_failure()
    
    scheduler = SlurmScheduler()
    with pytest.raises(SubmissionError):
        scheduler.submit_job("test_script.sh")
    
    # Test job failure
    helper.restore_normal_operation()
    job_id = helper.submit_test_job()
    helper.simulate_job_failure(job_id)
    
    status = scheduler.check_status(job_id)
    assert status == "FAILED"
```

### 4. Script Generation Testing

Validate generated SLURM scripts:

```python
def test_script_generation(slurm_with_standardized_env):
    """Test SLURM script generation."""
    from benchpro.tests.fixtures import assert_slurm_directives_present
    
    generator = SlurmScriptGenerator()
    script_content = generator.generate_script(template_path, variables)
    
    # Verify SLURM directives
    expected_directives = {
        "J": "test_job",
        "N": "2",
        "ntasks-per-node": "16",
        "t": "01:00:00"
    }
    
    assert_slurm_directives_present(script_content, expected_directives)
    
    # Test that script can be submitted
    mock_slurm = slurm_with_standardized_env["mock_slurm"]
    output = mock_slurm.submit_job(script_path)
    job_id = output.split()[-1]
    
    # Verify job properties match directives
    job = mock_slurm.get_job(job_id)
    assert job.job_name == "test_job"
    assert job.nodes == 2
```

## Utility Functions

### Script Creation

```python
from benchpro.tests.fixtures import create_slurm_script, create_minimal_slurm_script

# Create custom script
script_path = create_slurm_script("""#!/bin/bash
#SBATCH -J custom_job
#SBATCH -N 4

echo "Custom job"
""", temp_dir)

# Create minimal script
script_path = create_minimal_slurm_script("simple_job", temp_dir)
```

### Directive Validation

```python
from benchpro.tests.fixtures import assert_slurm_directives_present

script_content = generator.generate_script(template_path, variables)

expected_directives = {
    "J": "job_name",
    "N": "2",
    "t": "01:00:00",
    "p": "compute"
}

assert_slurm_directives_present(script_content, expected_directives)
```

### Job State Management

```python
# Wait for specific job state
success = mock_slurm.wait_for_job_state(job_id, JobState.RUNNING, timeout=5.0)

# Manually set job state
mock_slurm.set_job_state(job_id, JobState.FAILED)

# Get job details
job = mock_slurm.get_job(job_id)
print(f"Job {job.job_id} is {job.state.value}")
```

## Error Simulation

### Network Failures

```python
helper = SlurmTestHelper(mock_slurm)

# Simulate network issues
helper.simulate_network_failure()

# Test error handling
with pytest.raises(SubmissionError) as exc_info:
    scheduler.submit_job("test_script.sh")
assert "Connection timeout" in str(exc_info.value)

# Restore normal operation
helper.restore_normal_operation()
```

### Job Failures

```python
# Submit job normally
job_id = helper.submit_test_job()

# Simulate job failure
helper.simulate_job_failure(job_id)

# Verify failure handling
helper.assert_job_reached_state(job_id, JobState.FAILED)
```

## Best Practices

### 1. Use Appropriate Fixtures

- **`slurm_patched`**: For most component tests
- **`slurm_with_standardized_env`**: For integration tests
- **`mock_slurm_system_manual`**: For precise state control

### 2. Clean Up Resources

```python
def test_with_cleanup(slurm_patched):
    script_path = create_minimal_slurm_script("test_job")
    
    try:
        # Test logic here
        pass
    finally:
        # Always clean up
        if os.path.exists(script_path):
            os.unlink(script_path)
```

### 3. Use Test Helpers

```python
def test_with_helpers(slurm_patched):
    helper = SlurmTestHelper(slurm_patched)
    
    # Use helper methods for common operations
    job_id = helper.submit_test_job()
    helper.wait_for_completion(job_id)
    helper.assert_command_called("sbatch", times=1)
```

### 4. Test Edge Cases

```python
def test_edge_cases(slurm_patched):
    """Test various edge cases."""
    scheduler = SlurmScheduler()
    
    # Test nonexistent script
    with pytest.raises(SubmissionError):
        scheduler.submit_job("/nonexistent/script.sh")
    
    # Test invalid job ID
    with pytest.raises(StatusCheckError):
        scheduler.check_status("invalid_job_id")
```

### 5. Verify Command History

```python
def test_command_history(slurm_patched):
    helper = SlurmTestHelper(slurm_patched)
    
    # Perform operations
    job_id = helper.submit_test_job()
    scheduler = SlurmScheduler()
    scheduler.check_status(job_id)
    scheduler.cancel_job(job_id)
    
    # Verify expected commands were called
    helper.assert_command_called("sbatch", times=1)
    helper.assert_command_called("squeue")
    helper.assert_command_called("scancel", times=1)
```

## Migration Guide

### Updating Existing Tests

Replace manual subprocess mocking:

```python
# OLD: Manual mocking
@patch('subprocess.run')
def test_slurm_execution(mock_run):
    mock_run.return_value.stdout = "Submitted batch job 12345"
    # ... test logic

# NEW: Use SLURM fixtures
def test_slurm_execution(slurm_patched):
    # Automatic patching, realistic behavior
    # ... test logic
```

### Enhanced Test Coverage

Add comprehensive lifecycle testing:

```python
def test_comprehensive_lifecycle(slurm_patched):
    """Test complete job lifecycle."""
    helper = SlurmTestHelper(slurm_patched)
    
    # Submit job
    job_id = helper.submit_test_job()
    
    # Verify progression through states
    helper.assert_job_reached_state(job_id, JobState.PENDING)
    
    # Wait for running
    slurm_patched.wait_for_job_state(job_id, JobState.RUNNING)
    
    # Wait for completion
    helper.wait_for_completion(job_id)
    
    # Verify final state
    helper.assert_job_reached_state(job_id, JobState.COMPLETED)
```

## Benefits

### For Developers

1. **Faster Tests**: No need for actual SLURM installation
2. **Reliable Tests**: Consistent, predictable behavior
3. **Better Coverage**: Easy to test edge cases and error scenarios
4. **Easier Debugging**: Clear command history and job state tracking

### For Maintainability

1. **Centralized Mocking**: Single place to update SLURM simulation
2. **Consistent Interface**: Standardized fixtures across all tests
3. **Comprehensive Validation**: Realistic SLURM behavior simulation
4. **Future-Proof**: Easy to extend for new SLURM features

### For CI/CD

1. **No Dependencies**: Tests run without SLURM installation
2. **Fast Execution**: Mock system runs at full speed
3. **Deterministic**: Consistent results across environments
4. **Isolated**: Tests don't interfere with real SLURM systems

## Implementation Issues & Resolutions

During the implementation of the centralized SLURM testing infrastructure, several critical issues were identified and resolved. This section documents these fixes for future reference and troubleshooting.

### Issue #1: Missing Import Errors ✅ RESOLVED

**Problem**: Tests failing with `NameError: name 'get_standard_system_data' is not defined`

**Root Cause**: Test files were missing imports for centralized test data functions after refactoring to use the new fixtures.

**Solution**: Added proper imports to all test files:
```python
from benchpro.tests.fixtures.test_data import (
    get_standard_template,
    get_standard_system_data,
    get_standard_application_profile
)
```

**Files Modified**: `benchpro/tests/test_slurm_integration.py`

### Issue #2: SLURM Directives Parsing Failure ✅ RESOLVED

**Problem**: Generated SLURM scripts had malformed directives without newlines, causing jobs to be created with default values instead of specified configurations (e.g., nodes=1 instead of nodes=2).

**Root Cause**: The SLURM directives template in `SLURM_DIRECTIVES_BLOCK` was missing newlines between conditional blocks, resulting in concatenated directives like:
```bash
#SBATCH -J test_job
#SBATCH -N 2#SBATCH --ntasks-per-node=16#SBATCH -t 02:00:00
```

**Solution**: Fixed the Jinja2 template formatting in `benchpro/templates/standard_blocks.py`:
```python
content="""#SBATCH -J {{ job.name }}
{% if job.nodes %}#SBATCH -N {{ job.nodes }}
{% endif %}{% if job.tasks_per_node %}#SBATCH --ntasks-per-node={{ job.tasks_per_node }}
{% endif %}{% if job.time_limit %}#SBATCH -t {{ job.time_limit }}
{% endif %}...
```

**Files Modified**: `benchpro/templates/standard_blocks.py`

### Issue #3: Network Failure Simulation Not Working ✅ RESOLVED

**Problem**: Network failure tests expected "Connection timeout" error but received "Failed to parse job ID from output" instead.

**Root Cause**: The mock system wasn't properly simulating `subprocess.CalledProcessError` exceptions. The `SlurmScheduler` uses `subprocess.run` with `check=True`, which should raise `CalledProcessError` for non-zero return codes, but the mock was returning a `MagicMock` object that didn't automatically raise this exception.

**Solution**: Enhanced `MockSlurmCommands.run_command` to properly simulate subprocess behavior:
```python
# Simulate subprocess.run behavior with check=True
if result.returncode != 0 and kwargs.get('check', False):
    import subprocess
    raise subprocess.CalledProcessError(
        result.returncode, cmd, output=result.stdout, stderr=result.stderr
    )
```

**Files Modified**: `benchpro/tests/fixtures/mock_slurm.py`

### Issue #4: Invalid Job ID Status Check Not Raising Exception ✅ RESOLVED

**Problem**: `scheduler.check_status("invalid_job_id")` was returning "UNKNOWN" instead of raising `StatusCheckError` as expected by tests.

**Root Cause**: The `SlurmScheduler.check_status` method was designed to return "UNKNOWN" when both `squeue` and `sacct` commands couldn't find a job, but tests expected an exception for invalid job IDs.

**Analysis**: 
- `squeue` returns returncode=1 for invalid job IDs
- `sacct` returns returncode=0 even for invalid job IDs (with empty output)
- The scheduler logic needed to recognize this pattern as an invalid job ID scenario

**Solution**: Modified `SlurmScheduler.check_status` to raise `StatusCheckError` when `squeue` fails (indicating invalid job ID):
```python
# squeue failed and sacct has no results - likely invalid job ID
if squeue_failed:
    raise StatusCheckError(f"Job ID {job_id} not found - invalid job ID")
```

**Files Modified**: `benchpro/executor/scheduler.py`

### Issue #5: Mock Exception Propagation ✅ RESOLVED

**Problem**: Exceptions raised by the mock SLURM system weren't being properly propagated through the command interface.

**Root Cause**: The `MockSlurmCommands.run_command` method wasn't catching exceptions from the underlying mock system calls.

**Solution**: Added proper exception handling in the mock command interface:
```python
try:
    status = self.slurm_system.check_status(job_id, use_sacct=False)
    result.stdout = status
except Exception as e:
    result.returncode = 1
    result.stderr = str(e)
```

**Files Modified**: `benchpro/tests/fixtures/mock_slurm.py`

### Testing Results

After implementing all fixes:
- ✅ All 16 SLURM integration tests passing
- ✅ Proper SLURM directive parsing and job configuration
- ✅ Realistic error simulation and handling
- ✅ Comprehensive status checking with appropriate exceptions
- ✅ End-to-end template integration working correctly

### Lessons Learned

1. **Template Formatting**: Jinja2 templates require careful attention to whitespace and newlines, especially for configuration files like SLURM scripts.

2. **Mock Realism**: Mock systems must accurately simulate real system behavior, including error conditions and return codes.

3. **Exception Handling**: Proper exception propagation is critical for testing error scenarios effectively.

4. **Integration Testing**: Component-level mocking isn't sufficient; integration tests reveal issues that unit tests miss.

5. **Centralized Fixtures**: Moving to centralized test data requires systematic import updates across all test files.

## Conclusion

The new mock SLURM testing system provides a robust, maintainable solution for testing SLURM functionality without external dependencies. It integrates seamlessly with the existing centralized test infrastructure while providing comprehensive coverage of SLURM job lifecycles, error scenarios, and edge cases.

Key advantages:
- **Realistic simulation** of SLURM behavior
- **Easy integration** with existing tests
- **Comprehensive coverage** including error scenarios
- **Maintainable architecture** with centralized configuration
- **Developer-friendly** utilities and helpers

This solution enables confident testing of SLURM functionality while maintaining fast, reliable, and comprehensive test coverage. 