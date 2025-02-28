"""Tests for the scheduler executor base class."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import AsyncMock, Mock, patch

from benchpro.core.executor.scheduler import SchedulerExecutor
from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.ports.executor import ExecutionError, ResourceError

class MockSchedulerExecutor(SchedulerExecutor):
    """Mock scheduler executor for testing the base class."""
    
    async def _submit_to_scheduler(self, job: Job, script_path: Path) -> str:
        """Mock submission that returns a job ID."""
        return "test_job_123"
        
    async def _cancel_scheduler_job(self, scheduler_job_id: str) -> None:
        """Mock job cancellation."""
        pass
        
    async def _get_scheduler_job_status(self, scheduler_job_id: str) -> str:
        """Mock status check."""
        return "RUNNING"
        
    def _translate_resources(self, job: Job) -> Dict[str, str]:
        """Mock resource translation."""
        return {
            "nodes": "1",
            "cores": "4",
            "memory": "8G",
            "walltime": "1:00:00"
        }
        
    async def validate_resources(self, job: Job) -> None:
        """Mock resource validation."""
        pass

    async def get_resource_usage(self, job: Job) -> Dict[str, float]:
        """Mock resource usage."""
        return {
            "memory_mb": 1024.0,
            "virtual_memory_mb": 2048.0,
            "cpu_time": 60.0
        }

    # Base Executor abstract methods
    async def prepare(self, task: Task) -> None:
        """Mock prepare implementation."""
        pass

    async def run(self, task: Task) -> None:
        """Mock run implementation."""
        pass

    async def status(self, task: Task) -> TaskState:
        """Mock status implementation."""
        return TaskState.RUNNING

    async def stop(self, task: Task) -> None:
        """Mock stop implementation."""
        pass

    async def cleanup(self, task: Task) -> None:
        """Mock cleanup implementation."""
        pass

@pytest.fixture
def mock_executor(tmp_path):
    """Create a mock scheduler executor instance."""
    return MockSchedulerExecutor(tmp_path)

@pytest.fixture
def job(tmp_path):
    """Create a test job."""
    task_dir = tmp_path / "task"
    job_dir = tmp_path / "job"
    
    # Create directories
    task_dir.mkdir(parents=True)
    job_dir.mkdir(parents=True)
    
    task = Task(
        name="test_task",
        working_dir=task_dir,
        variables={"command": "echo test"}
    )
    
    return Job(
        name="test_job",
        working_dir=job_dir,
        tasks=[task],
        resources={"cores": 4, "memory": "8G"}
    )

@pytest.mark.asyncio
async def test_submit_job_basic(mock_executor, job):
    """Test basic job submission flow."""
    await mock_executor.submit_job(job)
    assert job.id in mock_executor._job_ids
    assert mock_executor._job_ids[job.id] == "test_job_123"
    assert job.state == JobState.RUNNING

@pytest.mark.asyncio
async def test_submit_job_script_generation(mock_executor, job):
    """Test job script generation."""
    await mock_executor.submit_job(job)
    script_path = job.working_dir / "job.sh"
    assert script_path.exists()
    content = script_path.read_text()
    assert "#nodes=1" in content
    assert "#cores=4" in content
    assert "#memory=8G" in content
    assert "echo test" in content

@pytest.mark.asyncio
async def test_submit_job_resource_validation_failure(mock_executor, job):
    """Test resource validation failure during submission."""
    mock_executor.validate_resources = AsyncMock(side_effect=ResourceError("Not enough resources"))
    
    with pytest.raises(ResourceError, match="Not enough resources"):
        await mock_executor.submit_job(job)
    assert job.state == JobState.CREATED

@pytest.mark.asyncio
async def test_submit_job_submission_failure(mock_executor, job):
    """Test submission failure handling."""
    mock_executor._submit_to_scheduler = AsyncMock(side_effect=ExecutionError("Submission failed"))
    
    with pytest.raises(ExecutionError, match="Submission failed"):
        await mock_executor.submit_job(job)
    assert job.state == JobState.CREATED

@pytest.mark.asyncio
async def test_cancel_job(mock_executor, job):
    """Test job cancellation."""
    await mock_executor.submit_job(job)
    await mock_executor.cancel_job(job)
    assert job.state == JobState.CANCELLED

@pytest.mark.asyncio
async def test_cancel_nonexistent_job(mock_executor, job):
    """Test cancelling a job that wasn't submitted."""
    with pytest.raises(ExecutionError, match="No scheduler job ID found"):
        await mock_executor.cancel_job(job)

@pytest.mark.asyncio
async def test_get_job_status(mock_executor, job):
    """Test getting job status."""
    await mock_executor.submit_job(job)
    status = await mock_executor.get_job_status(job)
    assert status["status"] == "RUNNING"

@pytest.mark.asyncio
async def test_cleanup_job(mock_executor, job):
    """Test job cleanup."""
    await mock_executor.submit_job(job)
    await mock_executor.cleanup_job(job)
    assert job.id not in mock_executor._job_ids 