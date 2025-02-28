"""Tests for local executor."""

import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from pytest_mock import MockerFixture

from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.executor.local import LocalExecutor
from benchpro.core.ports.executor import ExecutionError, ResourceError
from benchpro.core.services.settings import Settings
from benchpro.core.domain.errors import TaskExecutionError


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
    resources = {"cores": 4, "memory": "8G", "disk_space": "50G"}
    
    return {
        "name": "test_job",
        "working_dir": working_dir,
        "tasks": [task],
        "resources": resources,
    }


@pytest.fixture
def mock_settings():
    """Mock settings with controlled max_running_tasks."""
    with patch('benchpro.core.services.settings.Settings') as mock:
        settings_instance = mock.return_value
        settings_instance.get.return_value = 2  # Default to 2 max tasks
        yield settings_instance


@pytest.fixture
def executor(tmp_path):
    """Create a test executor."""
    return LocalExecutor(working_dir=tmp_path)


@pytest.fixture
def mock_system_resources(mocker):
    """Mock system resources."""
    # Mock CPU count
    mocker.patch("psutil.cpu_count", return_value=8)
    
    # Mock memory info
    mock_memory = mocker.Mock()
    mock_memory.total = 16 * 1024 * 1024 * 1024  # 16GB
    mock_memory.available = 12 * 1024 * 1024 * 1024  # 12GB
    mocker.patch("psutil.virtual_memory", return_value=mock_memory)
    
    # Mock disk usage
    mock_disk = mocker.Mock()
    mock_disk.free = 100 * 1024 * 1024 * 1024  # 100GB
    mocker.patch("psutil.disk_usage", return_value=mock_disk)
    
    return {
        "cpu_count": 8,
        "total_memory": 16 * 1024 * 1024 * 1024,
        "available_memory": 12 * 1024 * 1024 * 1024,
        "free_disk": 100 * 1024 * 1024 * 1024
    }


@pytest.fixture
def mock_subprocess(mocker: MockerFixture) -> AsyncMock:
    """Mock subprocess behavior."""
    mock_process = mocker.AsyncMock()
    mock_process.returncode = 0  # Default to success
    
    async def delayed_communicate():
        await asyncio.sleep(0.2)  # Add delay
        return (b"", b"")
    
    mock_process.communicate = mocker.AsyncMock(side_effect=delayed_communicate)
    mock_process.wait = mocker.AsyncMock()
    mock_process.terminate = mocker.AsyncMock()
    
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
    """Test resource validation with sufficient CPU cores."""
    # Mock CPU count to be more than requested
    mocker.patch("psutil.cpu_count", return_value=8)

    # Mock available memory to be more than requested
    mock_memory = mocker.Mock()
    mock_memory.available = 16 * 1024 * 1024 * 1024  # 16GB
    mocker.patch("psutil.virtual_memory", return_value=mock_memory)

    job = Job(**valid_job_data)
    # Should not raise an error
    await executor.validate_resources(job)


@pytest.mark.asyncio
async def test_validate_resources_insufficient_memory(
    executor: LocalExecutor,
    valid_job_data: dict,
    mocker: MockerFixture,
):
    """Test resource validation with insufficient memory."""
    # Mock available memory to be more than requested
    mock_memory = mocker.Mock()
    mock_memory.available = 16 * 1024 * 1024 * 1024  # 16GB
    mocker.patch("psutil.virtual_memory", return_value=mock_memory)

    job = Job(**valid_job_data)
    # Should not raise an error
    await executor.validate_resources(job)


@pytest.mark.asyncio
async def test_validate_resources_sufficient(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
):
    """Test resource validation with sufficient resources."""
    job = Job(**valid_job_data)
    await executor.validate_resources(job)  # Should not raise


@pytest.mark.asyncio
async def test_submit_job_success(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mock_subprocess,
):
    """Test successful job submission."""
    job = Job(**valid_job_data)
    
    # Start job in background
    submit_task = asyncio.create_task(executor.submit_job(job))
    await asyncio.sleep(0.1)  # Give time for tasks to start
    
    # Verify job is running
    assert job.state == JobState.RUNNING
    assert len(executor._processes) == 1
    
    # Complete the job
    await submit_task
    
    # Verify completion
    assert job.tasks[0].state == TaskState.COMPLETED
    assert job.state == JobState.COMPLETED


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

    # Mock path validation
    mocker.patch(
        "benchpro.core.validation.validators.validate_file",
        return_value=script
    )

    job = Job(**valid_job_data)
    job.tasks[0].template_path = script

    # Mock execute_task to set states before raising error
    async def mock_execute_task(task, job, working_dir):
        task.transition_to(TaskState.FAILED, "Task failed with exit code 1: error message")
        job.state = JobState.FAILED
        raise TaskExecutionError("Task failed with exit code 1: error message")

    executor._process_manager.execute_task = mock_execute_task

    # Run the job and expect it to fail
    with pytest.raises(TaskExecutionError) as exc_info:
        await executor.submit_job(job)

    # Check error message
    assert str(exc_info.value) == "Task failed with exit code 1: error message"

    # Check states
    assert job.state == JobState.FAILED
    assert job.tasks[0].state == TaskState.FAILED


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
    mock_process.returncode = None
    mock_process.communicate = mocker.AsyncMock(side_effect=asyncio.CancelledError)
    mock_process.wait = mocker.AsyncMock()
    mock_process.terminate = mocker.AsyncMock()
    
    mocker.patch(
        "asyncio.create_subprocess_exec",
        mocker.AsyncMock(return_value=mock_process),
    )
    
    job = Job(**valid_job_data)
    
    # Start job in background
    task = asyncio.create_task(executor.submit_job(job))
    await asyncio.sleep(0.1)  # Let job start
    
    # Cancel job
    await executor.cancel_job(job)
    with pytest.raises(asyncio.CancelledError):
        await task
    
    assert job.tasks[0].state == TaskState.CANCELLED


@pytest.mark.asyncio
async def test_get_job_status(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mock_subprocess,
):
    """Test getting job status."""
    job = Job(**valid_job_data)
    
    # Start job in background
    submit_task = asyncio.create_task(executor.submit_job(job))
    await asyncio.sleep(0.1)  # Let job start
    
    # Check initial status
    status = await executor.get_job_status(job)
    assert status["state"] == "running"
    assert status["tasks"]["running"] == 1
    
    # Complete the job
    await submit_task
    
    # Check final status
    status = await executor.get_job_status(job)
    assert status["state"] == "completed"
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
    
    # Start job
    task = asyncio.create_task(executor.submit_job(job))
    await asyncio.sleep(0.1)  # Let job start
    
    # Check resource usage
    usage = await executor.get_resource_usage(job)
    assert usage["cores"] == 4  # From valid_job_data
    assert usage["memory"] == "8G"  # From valid_job_data
    
    # Complete job
    mock_subprocess.returncode = 0
    await task


@pytest.mark.asyncio
async def test_cleanup_job(
    executor: LocalExecutor,
    valid_job_data: dict,
    mock_system_resources,
    mock_subprocess,
):
    """Test job cleanup."""
    job = Job(**valid_job_data)
    
    # Start job in background
    submit_task = asyncio.create_task(executor.submit_job(job))
    await asyncio.sleep(0.1)  # Let job start
    
    # Check process is tracked
    assert len(executor._processes) == 1
    
    # Complete the job
    await submit_task
    
    # Clean up
    await executor.cleanup_job(job)
    assert len(executor._processes) == 0
    assert len(executor._monitors) == 0


async def create_sleep_task(name: str, duration: float) -> Task:
    """Create a task that sleeps for the specified duration."""
    # Create a temporary script that sleeps
    script_path = Path(f"/tmp/sleep_{name}.sh")
    script_path.write_text(f"#!/bin/bash\nsleep {duration}")
    script_path.chmod(0o755)
    
    return Task(
        name=name,
        working_dir="/tmp",
        template_path=script_path
    )


@pytest.mark.asyncio
async def test_concurrent_task_limit(executor, mock_settings):
    """Test that max concurrent tasks limit is respected."""
    # Set max running tasks to 1
    mock_settings.get.return_value = 1

    # Create 3 tasks with different durations
    tasks = [
        await create_sleep_task("task1", 0.3),
        await create_sleep_task("task2", 0.2),
        await create_sleep_task("task3", 0.1)
    ]

    job = Job(
        name="test_job",
        working_dir=Path("/tmp"),
        tasks=tasks,
        resources={"cores": 1, "memory": "1G", "walltime": 3600}
    )

    # Submit job
    start_time = time.time()
    await executor.submit_job(job)
    await asyncio.sleep(0.1)  # Give time for tasks to start

    # Verify only one task is running
    status = await executor.get_job_status(job)
    assert status["tasks"]["running"] <= 1

    # Wait for all tasks to complete
    await asyncio.sleep(0.5)
    end_time = time.time()

    # Verify total time is at least sum of task durations (0.6s)
    assert end_time - start_time >= 0.6


@pytest.mark.asyncio
async def test_semaphore_queueing(executor, mock_settings):
    """Test that tasks queue up properly when semaphore is full."""
    # Set max running tasks to 1
    mock_settings.get.return_value = 1

    # Create 3 tasks with different durations
    tasks = [
        await create_sleep_task("task1", 0.3),
        await create_sleep_task("task2", 0.2),
        await create_sleep_task("task3", 0.1)
    ]

    job = Job(
        name="test_job",
        working_dir=Path("/tmp"),
        tasks=tasks,
        resources={"cores": 1, "memory": "1G", "walltime": 3600}
    )

    # Submit job
    await executor.submit_job(job)
    await asyncio.sleep(0.1)  # Give time for first task to start

    # Verify only one task is running
    status = await executor.get_job_status(job)
    assert status["tasks"]["running"] <= 1

    # Wait for all tasks to complete
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_semaphore_release_on_failure(executor, mock_settings, mocker, tmp_path):
    """Test that semaphore is released when a task fails."""
    # Set max running tasks to 1
    mock_settings.get.return_value = 1
    
    # Create failing script
    script = tmp_path / "fail.sh"
    script.write_text("#!/bin/bash\nexit 1")
    script.chmod(0o755)
    
    # Mock path validation
    mocker.patch(
        "benchpro.core.validation.validators.validate_file",
        return_value=script
    )
    
    # Create a failing task and a normal task
    failing_task = Task(
        name="failing_task",
        working_dir=Path("/tmp"),
        template_path=script
    )
    
    normal_task = await create_sleep_task("normal_task", 0.1)
    
    job = Job(
        name="test_job",
        working_dir=Path("/tmp"),
        tasks=[failing_task, normal_task],
        resources={"cores": 1, "memory": "1G", "walltime": 3600}
    )
    
    # Mock subprocess to fail for the failing task and succeed for the normal task
    mock_process_fail = mocker.AsyncMock()
    mock_process_fail.returncode = 1
    mock_process_fail.communicate = mocker.AsyncMock(return_value=(b"", b"error message"))
    
    mock_process_normal = mocker.AsyncMock()
    mock_process_normal.returncode = 0
    mock_process_normal.communicate = mocker.AsyncMock(return_value=(b"", b""))
    
    # Mock create_subprocess_exec to return different processes for each task
    create_subprocess_mock = mocker.AsyncMock()
    create_subprocess_mock.side_effect = [mock_process_fail, mock_process_normal]
    mocker.patch("asyncio.create_subprocess_exec", create_subprocess_mock)
    
    error_raised = False
    try:
        await executor.submit_job(job)
    except TaskExecutionError as e:
        error_raised = True
        assert "Task failed with exit code 1: error message" in str(e)

    assert error_raised, "Expected TaskExecutionError was not raised"
    assert job.state == JobState.FAILED
    assert job.tasks[0].state == TaskState.FAILED
    assert job.tasks[0].error == "Task failed with exit code 1: error message"
    assert job.tasks[1].state == TaskState.PENDING
    assert executor._semaphore._value == 1  # Verify semaphore was released


@pytest.mark.asyncio
async def test_semaphore_release_on_cancel(executor, mock_settings):
    """Test that semaphore is released when a task is cancelled."""
    # Set max running tasks to 1
    mock_settings.get.return_value = 1
    
    # Create two long-running tasks
    tasks = [
        await create_sleep_task("task1", 2.0),
        await create_sleep_task("task2", 2.0)
    ]
    
    job = Job(
        name="test_job",
        working_dir="/tmp",
        tasks=tasks,
        resources={"cores": 1, "memory": "1G", "walltime": 3600}
    )
    
    # Submit job
    submit_task = asyncio.create_task(executor.submit_job(job))
    await asyncio.sleep(0.1)  # Let job start
    
    # Cancel job
    await executor.cancel_job(job)
    with pytest.raises(asyncio.CancelledError):
        await submit_task
    
    # Check that both tasks are cancelled
    assert all(task.state == TaskState.CANCELLED for task in tasks)


@pytest.mark.asyncio
async def test_settings_max_tasks_honored(tmp_path, mock_settings):
    """Test that the max_running_tasks setting is honored."""
    # Test with different max_running_tasks values
    for max_tasks in [1, 3, 5]:
        mock_settings.get.return_value = {"executor": {"max_running_tasks": max_tasks}}
        
        # Create a new executor to pick up the new setting
        executor = LocalExecutor(working_dir=tmp_path, settings=mock_settings)
        assert executor._semaphore._value == max_tasks