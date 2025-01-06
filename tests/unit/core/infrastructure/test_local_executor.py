"""Tests for local executor."""

import asyncio
import os
from pathlib import Path
from typing import Dict

import psutil
import pytest
from pytest_mock import MockerFixture

from benchpro.core.domain.job import Job, JobResources, JobState
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.infrastructure.local_executor import LocalExecutor
from benchpro.core.ports.executor import ExecutionError, ResourceError


@pytest.fixture
def valid_task_data(tmp_path: Path) -> dict:
    """Create valid task data for testing."""
    working_dir = tmp_path / "work"
    working_dir.mkdir()
    template = tmp_path / "job.sh"
    template.write_text("#!/bin/bash\necho 'test'\nsleep 1")
    template.chmod(0o755)
    
    return {
        "name": "test_task",
        "working_dir": working_dir,
        "template_path": template,
        "variables": {"cores": 4, "memory": "8G"},
    }


@pytest.fixture
def valid_job_data(tmp_path: Path, valid_task_data: dict) -> dict:
    """Create valid job data for testing."""
    working_dir = tmp_path / "job"
    working_dir.mkdir()
    
    task = Task(**valid_task_data)
    resources = JobResources(cores=4, memory="8G")
    
    return {
        "name": "test_job",
        "working_dir": working_dir,
        "tasks": [task],
        "resources": resources,
    }


@pytest.fixture
def executor() -> LocalExecutor:
    """Create a local executor."""
    return LocalExecutor()


@pytest.fixture
def mock_system_resources(mocker: MockerFixture):
    """Mock system resources."""
    # Mock CPU count
    mocker.patch("psutil.cpu_count", return_value=8)
    
    # Mock memory
    mock_memory = mocker.Mock()
    mock_memory.available = 16 * 1024 * 1024 * 1024  # 16GB
    mocker.patch("psutil.virtual_memory", return_value=mock_memory)
    
    # Mock process
    mock_process = mocker.Mock()
    mock_process.cpu_percent.return_value = 10.0
    mock_process.memory_info.return_value = mocker.Mock(rss=1024 * 1024 * 1024)  # 1GB
    mock_process.io_counters.return_value = mocker.Mock(
        read_bytes=1024,
        write_bytes=2048,
    )
    mocker.patch("psutil.Process", return_value=mock_process)


@pytest.fixture
def mock_subprocess(mocker: MockerFixture):
    """Mock subprocess execution."""
    # Mock process
    mock_process = mocker.AsyncMock()
    mock_process.pid = 12345
    mock_process.returncode = None  # Set to None initially
    mock_process.communicate = mocker.AsyncMock(return_value=(b"stdout", b"stderr"))
    mock_process.wait = mocker.AsyncMock()
    mock_process.terminate = mocker.AsyncMock()
    
    # Mock create_subprocess_exec
    mocker.patch(
        "asyncio.create_subprocess_exec",
        mocker.AsyncMock(return_value=mock_process),
    )
    
    return mock_process


@pytest.mark.asyncio
async def test_validate_resources_success(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
):
    """Test resource validation with sufficient resources."""
    job = Job(**valid_job_data)
    await executor.validate_resources(job)  # Should not raise


@pytest.mark.asyncio
async def test_validate_resources_insufficient_cores(
    executor: LocalExecutor,
    valid_job_data: dict,
    mocker: MockerFixture,
):
    """Test resource validation with insufficient CPU cores."""
    # Mock CPU count to be less than requested
    mocker.patch("psutil.cpu_count", return_value=2)
    
    job = Job(**valid_job_data)
    with pytest.raises(ResourceError, match="Requested 4 cores but only 2 available"):
        await executor.validate_resources(job)


@pytest.mark.asyncio
async def test_validate_resources_insufficient_memory(
    executor: LocalExecutor,
    valid_job_data: dict,
    mocker: MockerFixture,
):
    """Test resource validation with insufficient memory."""
    # Mock available memory to be less than requested
    mock_memory = mocker.Mock()
    mock_memory.available = 4 * 1024 * 1024 * 1024  # 4GB
    mocker.patch("psutil.virtual_memory", return_value=mock_memory)
    
    job = Job(**valid_job_data)
    with pytest.raises(ResourceError, match="Requested 8G but only"):
        await executor.validate_resources(job)


@pytest.mark.asyncio
async def test_submit_job_success(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mock_subprocess,
):
    """Test successful job submission."""
    job = Job(**valid_job_data)
    await executor.submit_job(job)
    
    assert job.state == JobState.RUNNING
    assert job.tasks[0].state == TaskState.RUNNING
    assert len(executor._running_processes) == 1
    
    # Simulate task completion
    mock_subprocess.returncode = 0
    await asyncio.sleep(0.1)  # Let task state update
    
    assert job.tasks[0].state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_submit_job_failure(
    executor: LocalExecutor,
    valid_job_data: dict,
    tmp_path: Path,
    mock_system_resources,
    mocker: MockerFixture,
):
    """Test job submission with failing task."""
    # Create failing script
    script = tmp_path / "fail.sh"
    script.write_text("#!/bin/bash\nexit 1")
    script.chmod(0o755)
    
    # Mock subprocess
    mock_process = mocker.AsyncMock()
    mock_process.pid = 12345
    mock_process.returncode = 1
    mock_process.communicate = mocker.AsyncMock(return_value=(b"", b"error message"))
    mock_process.wait = mocker.AsyncMock()
    mock_process.terminate = mocker.AsyncMock()
    
    mocker.patch(
        "asyncio.create_subprocess_exec",
        mocker.AsyncMock(return_value=mock_process),
    )
    
    job = Job(**valid_job_data)
    job.tasks[0].template_path = script
    
    await executor.submit_job(job)
    await asyncio.sleep(0.1)  # Let task state update
    
    assert job.tasks[0].state == TaskState.FAILED
    assert job.tasks[0].error is not None
    assert "error message" in job.tasks[0].error


@pytest.mark.asyncio
async def test_cancel_job(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mocker: MockerFixture,
):
    """Test job cancellation."""
    # Mock subprocess
    mock_process = mocker.AsyncMock()
    mock_process.pid = 12345
    mock_process.returncode = None
    mock_process.communicate = mocker.AsyncMock(side_effect=asyncio.CancelledError)
    mock_process.wait = mocker.AsyncMock()
    mock_process.terminate = mocker.AsyncMock()
    
    # Make terminate a coroutine that sets returncode
    async def terminate():
        mock_process.returncode = -15  # SIGTERM
    mock_process.terminate = terminate
    
    mocker.patch(
        "asyncio.create_subprocess_exec",
        mocker.AsyncMock(return_value=mock_process),
    )
    
    job = Job(**valid_job_data)
    await executor.submit_job(job)
    await asyncio.sleep(0.1)  # Let task start
    
    await executor.cancel_job(job)
    assert job.state == JobState.CANCELLED
    assert job.tasks[0].state == TaskState.CANCELLED
    assert len(executor._running_processes) == 0


@pytest.mark.asyncio
async def test_get_job_status(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mock_subprocess,
):
    """Test getting job status."""
    job = Job(**valid_job_data)
    await executor.submit_job(job)
    
    status = await executor.get_job_status(job)
    assert status["state"] == "running"
    assert status["tasks"]["total"] == 1
    assert status["tasks"]["running"] == 1
    
    # Simulate task completion
    mock_subprocess.returncode = 0
    await asyncio.sleep(0.1)  # Let task state update
    
    status = await executor.get_job_status(job)
    assert status["tasks"]["completed"] == 1


@pytest.mark.asyncio
async def test_get_resource_usage(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mock_subprocess,
):
    """Test getting resource usage."""
    job = Job(**valid_job_data)
    await executor.submit_job(job)
    await asyncio.sleep(0.1)  # Let task start
    
    usage = await executor.get_resource_usage(job)
    assert "cpu_percent" in usage
    assert "memory_bytes" in usage
    assert "io_read_bytes" in usage
    assert "io_write_bytes" in usage
    
    await executor.cancel_job(job)  # Cleanup


@pytest.mark.asyncio
async def test_cleanup_job(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mock_subprocess,
):
    """Test job cleanup."""
    job = Job(**valid_job_data)
    await executor.submit_job(job)
    await asyncio.sleep(0.1)  # Let task start
    
    await executor.cleanup_job(job)
    assert len(executor._running_processes) == 0 