"""Tests for the base executor interface."""

import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from benchpro.core.executor.base import (
    Executor, ExecutorError, TaskExecutionError, ResourceError
)
from benchpro.core.domain import Task, TaskState

class MockExecutor(Executor):
    """Mock executor for testing the base interface."""
    
    def __init__(self, working_dir: Path, env: Optional[Dict[str, str]] = None):
        """Initialize the mock executor."""
        super().__init__(working_dir, env)
        self.validate_called = False
        self.prepare_called = False
        self.run_called = False
        self.status_called = False
        self.stop_called = False
        self.cleanup_called = False
        self._task_state = TaskState.PENDING
    
    async def validate_resources(self, task: Task) -> bool:
        """Mock resource validation."""
        self.validate_called = True
        return True
    
    async def prepare(self, task: Task) -> None:
        """Mock preparation."""
        self.prepare_called = True
    
    async def run(self, task: Task) -> None:
        """Mock task execution."""
        self.run_called = True
        self._task_state = TaskState.RUNNING
    
    async def status(self, task: Task) -> TaskState:
        """Mock status check."""
        self.status_called = True
        return self._task_state
    
    async def stop(self, task: Task) -> None:
        """Mock task stopping."""
        self.stop_called = True
        self._task_state = TaskState.CANCELLED
    
    async def cleanup(self, task: Task) -> None:
        """Mock cleanup."""
        self.cleanup_called = True

@pytest.fixture
def mock_executor(tmp_path):
    """Create a mock executor instance."""
    return MockExecutor(tmp_path)

@pytest.fixture
def mock_task(tmp_path):
    """Create a mock task for testing."""
    return Task(
        name="test-task",
        working_dir=tmp_path / "tasks" / "test-task",
        variables={
            "cores": 1,
            "memory": "1G",
            "walltime": 3600
        }
    )

@pytest.mark.asyncio
async def test_executor_initialization(tmp_path):
    """Test executor initialization."""
    env = {"TEST_VAR": "test_value"}
    executor = MockExecutor(tmp_path, env)
    assert executor.working_dir == tmp_path
    assert executor.env == env

@pytest.mark.asyncio
async def test_executor_default_env(tmp_path):
    """Test executor initialization with default environment."""
    executor = MockExecutor(tmp_path)
    assert executor.env == {}

@pytest.mark.asyncio
async def test_executor_validate_resources(mock_executor, mock_task):
    """Test resource validation."""
    result = await mock_executor.validate_resources(mock_task)
    assert result is True
    assert mock_executor.validate_called

@pytest.mark.asyncio
async def test_executor_prepare(mock_executor, mock_task):
    """Test task preparation."""
    await mock_executor.prepare(mock_task)
    assert mock_executor.prepare_called

@pytest.mark.asyncio
async def test_executor_run(mock_executor, mock_task):
    """Test task execution."""
    await mock_executor.run(mock_task)
    assert mock_executor.run_called
    assert await mock_executor.status(mock_task) == TaskState.RUNNING

@pytest.mark.asyncio
async def test_executor_status(mock_executor, mock_task):
    """Test status checking."""
    state = await mock_executor.status(mock_task)
    assert state == TaskState.PENDING
    assert mock_executor.status_called

@pytest.mark.asyncio
async def test_executor_stop(mock_executor, mock_task):
    """Test task stopping."""
    await mock_executor.stop(mock_task)
    assert mock_executor.stop_called
    assert await mock_executor.status(mock_task) == TaskState.CANCELLED

@pytest.mark.asyncio
async def test_executor_cleanup(mock_executor, mock_task):
    """Test cleanup."""
    await mock_executor.cleanup(mock_task)
    assert mock_executor.cleanup_called

@pytest.mark.asyncio
async def test_executor_context_manager(mock_executor):
    """Test executor as context manager."""
    async with mock_executor as executor:
        assert isinstance(executor, Executor)

@pytest.mark.asyncio
async def test_executor_error_hierarchy():
    """Test executor error class hierarchy."""
    assert issubclass(TaskExecutionError, ExecutorError)
    assert issubclass(ResourceError, ExecutorError) 