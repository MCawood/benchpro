"""Tests for executor interface."""

import pytest
from typing import Dict

from benchpro.core.ports.executor import (
    Executor,
    ExecutorError,
    ResourceError,
    ExecutionError,
)


class MockExecutor(Executor):
    """Mock executor for testing interface."""
    
    async def validate_resources(self, job) -> None:
        """Mock resource validation."""
        pass

    async def submit_job(self, job) -> None:
        """Mock job submission."""
        pass

    async def cancel_job(self, job) -> None:
        """Mock job cancellation."""
        pass

    async def get_job_status(self, job) -> Dict[str, str]:
        """Mock status check."""
        return {"status": "running"}

    async def get_resource_usage(self, job) -> Dict[str, float]:
        """Mock resource usage check."""
        return {"cpu_percent": 50.0, "memory_gb": 4.0}

    async def cleanup_job(self, job) -> None:
        """Mock cleanup."""
        pass


class ErrorMockExecutor(Executor):
    """Mock executor that raises errors."""
    
    async def validate_resources(self, job) -> None:
        """Mock resource validation with error."""
        raise ResourceError("Not enough resources")

    async def submit_job(self, job) -> None:
        """Mock job submission with error."""
        raise ExecutionError("Submission failed")

    async def cancel_job(self, job) -> None:
        """Mock job cancellation with error."""
        raise ExecutionError("Cancellation failed")

    async def get_job_status(self, job) -> Dict[str, str]:
        """Mock status check with error."""
        raise ExecutionError("Status check failed")

    async def get_resource_usage(self, job) -> Dict[str, float]:
        """Mock resource usage check with error."""
        raise ExecutionError("Resource check failed")

    async def cleanup_job(self, job) -> None:
        """Mock cleanup with error."""
        raise ExecutionError("Cleanup failed")


@pytest.fixture
def mock_executor() -> Executor:
    """Create a mock executor."""
    return MockExecutor()


@pytest.fixture
def error_executor() -> Executor:
    """Create an error-raising mock executor."""
    return ErrorMockExecutor()


@pytest.mark.asyncio
async def test_executor_interface(mock_executor: Executor):
    """Test that executor interface methods work."""
    # All methods should complete without raising
    await mock_executor.validate_resources(None)
    await mock_executor.submit_job(None)
    await mock_executor.cancel_job(None)
    
    status = await mock_executor.get_job_status(None)
    assert isinstance(status, dict)
    assert "status" in status
    
    usage = await mock_executor.get_resource_usage(None)
    assert isinstance(usage, dict)
    assert "cpu_percent" in usage
    assert "memory_gb" in usage
    
    await mock_executor.cleanup_job(None)


@pytest.mark.asyncio
async def test_executor_errors(error_executor: Executor):
    """Test that executor errors are raised correctly."""
    with pytest.raises(ResourceError, match="Not enough resources"):
        await error_executor.validate_resources(None)
    
    with pytest.raises(ExecutionError, match="Submission failed"):
        await error_executor.submit_job(None)
    
    with pytest.raises(ExecutionError, match="Cancellation failed"):
        await error_executor.cancel_job(None)
    
    with pytest.raises(ExecutionError, match="Status check failed"):
        await error_executor.get_job_status(None)
    
    with pytest.raises(ExecutionError, match="Resource check failed"):
        await error_executor.get_resource_usage(None)
    
    with pytest.raises(ExecutionError, match="Cleanup failed"):
        await error_executor.cleanup_job(None)


def test_error_hierarchy():
    """Test executor error class hierarchy."""
    assert issubclass(ResourceError, ExecutorError)
    assert issubclass(ExecutionError, ExecutorError)
    
    # Ensure errors can be caught as ExecutorError
    try:
        raise ResourceError("test")
    except ExecutorError:
        pass
    
    try:
        raise ExecutionError("test")
    except ExecutorError:
        pass 