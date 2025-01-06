# BenchPRO Testing Guide

## Overview

BenchPRO follows a strict test-driven development approach. This guide outlines our testing strategy, requirements, and best practices.

## Testing Strategy

### 1. Test-First Development
- Write failing tests before implementation
- Cover edge cases and error scenarios
- Include integration tests from the start
- Document test scenarios and rationale

### 2. Test Categories

#### Unit Tests
```python
# Example task creation test
def test_task_creation():
    """Test task creation with valid parameters."""
    task = Task(
        id=uuid4(),
        name="test_task",
        working_dir=Path("/tmp/test"),
        template_path=Path("/tmp/test.sh"),
        variables={}
    )
    assert task.status == TaskStatus.CREATED
    assert task.validate() == []

def test_task_invalid_state_transition():
    """Test invalid task state transitions."""
    task = Task(...)
    with pytest.raises(InvalidStateTransition):
        task.status = TaskStatus.COMPLETED
```

#### Integration Tests
```python
# Example executor integration test
@pytest.mark.asyncio
async def test_local_executor():
    """Test local task execution."""
    executor = LocalExecutor()
    task = Task(...)
    job = await executor.submit(task)
    assert job.status == JobStatus.RUNNING
    result = await executor.wait(job)
    assert result.exit_code == 0
```

#### Resource Tests
```python
# Example resource allocation test
def test_resource_allocation():
    """Test resource allocation and tracking."""
    resources = TaskResources(
        cpu_cores=2,
        memory_gb=4,
        gpu_count=1
    )
    assert resources.validate()
    assert resources.total_memory == 4096  # MB
```

#### Configuration Tests
```python
# Example configuration test
def test_config_validation():
    """Test configuration validation."""
    config = Config.from_file("test_config.yaml")
    assert config.validate()
    with pytest.raises(ValidationError):
        config.resources.cpu_cores = -1
```

#### Template Tests
```python
# Example template test
def test_template_rendering():
    """Test template rendering with variables."""
    template = Template.load("job.sh.j2")
    result = template.render({"cores": 4, "memory": "8G"})
    assert "#SBATCH --cpus-per-task=4" in result
```

## Test Coverage Requirements

### Code Coverage Targets
- Unit test coverage > 80%
- Integration test coverage > 70%
- Critical path coverage > 90%

### Component Coverage
1. **Core Domain**
   - All model validations
   - State transitions
   - Error conditions
   - Edge cases

2. **Execution Framework**
   - Task submission
   - Job monitoring
   - Resource management
   - Error handling

3. **Resource Management**
   - Allocation logic
   - Usage tracking
   - Cleanup procedures
   - Error recovery

4. **Configuration**
   - Schema validation
   - Migration paths
   - User settings
   - Environment detection

5. **Templates**
   - Rendering logic
   - Variable substitution
   - Error handling
   - Performance

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
```

### Test Options
```bash
# Run with coverage report
pytest --cov=benchpro

# Run specific test markers
pytest -m "not slow"

# Run tests in parallel
pytest -n auto
```

## Writing Tests

### Test Structure
1. **Arrange**
   - Set up test data
   - Create necessary objects
   - Configure environment

2. **Act**
   - Execute the code under test
   - Capture outputs
   - Handle async operations

3. **Assert**
   - Verify results
   - Check state changes
   - Validate cleanup

### Best Practices
1. **Test Independence**
   - Each test should be self-contained
   - Clean up after each test
   - Don't rely on test order

2. **Clear Names**
   - Describe what is being tested
   - Include expected behavior
   - Note any special conditions

3. **Documentation**
   - Add docstrings to test functions
   - Explain complex scenarios
   - Document test data

4. **Error Cases**
   - Test failure scenarios
   - Verify error messages
   - Check error handling

## Test Data Management

### Test Fixtures
```python
@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id=uuid4(),
        name="test_task",
        working_dir=Path("/tmp/test"),
        template_path=Path("/tmp/test.sh"),
        variables={}
    )

@pytest.fixture
def mock_executor():
    """Create a mock executor for testing."""
    executor = Mock(spec=Executor)
    executor.submit.return_value = Job(...)
    return executor
```

### Test Resources
- Keep test data in `tests/data/`
- Use version control for test files
- Document data format and purpose
- Include edge case examples

## Continuous Integration

### CI Pipeline
1. **Setup**
   - Install dependencies
   - Configure environment
   - Prepare test data

2. **Test Execution**
   - Run all test categories
   - Generate coverage report
   - Check performance metrics

3. **Reporting**
   - Upload test results
   - Generate coverage badges
   - Notify on failures

### Quality Gates
- All tests must pass
- Coverage meets targets
- No new issues introduced
- Performance within limits 