"""Tests for the ProcessManager class."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from benchpro.core.domain import Task, Job, TaskState, JobState
from benchpro.core.executor.base import TaskExecutionError
from benchpro.core.executor.local.process import ProcessManager

@pytest.fixture
def process_manager():
    """Create a ProcessManager instance."""
    return ProcessManager()

@pytest.fixture
def test_script():
    """Create a temporary test script file."""
    script_path = Path("/tmp/test_script.sh")
    script_path.write_text("#!/bin/bash\necho 'test'")
    script_path.chmod(0o755)
    yield script_path
    script_path.unlink(missing_ok=True)

def create_mock_task(script):
    """Create a mock task for testing."""
    task = MagicMock()
    task.id = str(uuid.uuid4())
    task.name = "test_task"
    task.template_path = script
    task.state = TaskState.CREATED
    task.resources = {"cores": 2, "memory": "4G"}
    
    def transition_side_effect(new_state, error_msg=None):
        task.state = new_state
        if error_msg:
            task.error = error_msg
    
    task.transition_to = MagicMock(side_effect=transition_side_effect)
    return task

@pytest.fixture
def mock_task(test_script):
    """Create a mock task for testing."""
    return create_mock_task(test_script)

@pytest.fixture
def mock_job(test_script):
    """Create a mock job for testing."""
    task = create_mock_task(test_script)
    job = Job(
        name="test_job",
        working_dir=Path("/"),
        tasks=[task],
        resources={"cores": 2, "memory": "4G"},
        state=JobState.CREATED
    )
    return job

@pytest.mark.asyncio
async def test_execute_task_success(process_manager, mock_task, mock_job, test_script):
    """Test successful task execution."""
    assert mock_job.state == JobState.CREATED
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"stdout", b"stderr")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await process_manager.execute_task(mock_task, mock_job, Path("/tmp"))
        
    mock_task.transition_to.assert_any_call(TaskState.COMPLETED)
    assert mock_job.state == JobState.RUNNING

@pytest.mark.asyncio
async def test_execute_task_failure(process_manager, mock_task, mock_job, test_script):
    """Test task execution failure."""
    assert mock_job.state == JobState.CREATED
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"error message")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(TaskExecutionError, match="Task failed with exit code 1: error message"):
            await process_manager.execute_task(mock_task, mock_job, Path("/tmp"))
        
    mock_task.transition_to.assert_any_call(TaskState.FAILED)
    assert mock_job.state == JobState.FAILED
    assert mock_job.completed_at is not None

@pytest.mark.asyncio
async def test_execute_task_cancellation(process_manager, mock_task, mock_job, test_script):
    """Test task execution cancellation."""
    assert mock_job.state == JobState.CREATED
    mock_process = AsyncMock()
    mock_process.returncode = -15  # SIGTERM
    mock_process.communicate.return_value = (b"", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(asyncio.CancelledError):
            await process_manager.execute_task(mock_task, mock_job, Path("/tmp"))
        
    mock_task.transition_to.assert_any_call(TaskState.CANCELLED)
    assert mock_job.state == JobState.CANCELLED
    assert mock_job.completed_at is not None

@pytest.mark.asyncio
async def test_cancel_job(process_manager, mock_job):
    """Test job cancellation."""
    # Setup process mock
    mock_process = AsyncMock()
    mock_process.returncode = None
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.terminate = MagicMock()  # Not async
    process_manager._processes[mock_job.id] = mock_process

    # Setup monitor mock (just a Task)
    mock_monitor = AsyncMock()
    mock_monitor.cancel = MagicMock()  # Not async
    process_manager._monitors[mock_job.id] = mock_monitor

    await process_manager.cancel_job(mock_job)
    
    # Verify process handling
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()
    assert mock_job.id not in process_manager._processes
    
    # Verify monitor handling
    mock_monitor.cancel.assert_called_once()
    assert mock_job.id not in process_manager._monitors
    
    # Verify job state
    assert mock_job.state == JobState.CANCELLED
    for task in mock_job.tasks:
        assert task.state == TaskState.CANCELLED

@pytest.mark.asyncio
async def test_cancel_job_timeout(process_manager, mock_job):
    """Test job cancellation with timeout."""
    mock_process = AsyncMock()
    mock_process.returncode = None
    mock_process.wait = AsyncMock()
    mock_process.wait.side_effect = [asyncio.TimeoutError(), None]  # First call raises TimeoutError, second succeeds
    mock_process.terminate = MagicMock()  # Not async
    mock_process.kill = MagicMock()  # Not async
    process_manager._processes[mock_job.id] = mock_process

    await process_manager.cancel_job(mock_job)
    
    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()
    mock_process.wait.assert_called()
    assert mock_job.state == JobState.CANCELLED

def test_get_process(process_manager, mock_job):
    """Test getting a process for a job."""
    mock_process = AsyncMock()
    process_manager._processes[mock_job.id] = mock_process
    
    assert process_manager.get_process(mock_job.id) == mock_process
    assert process_manager.get_process("nonexistent") is None 