"""Tests for the LocalExecutor class."""

import asyncio
import pytest
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import re

from benchpro.core.domain import Task, Job, TaskState, JobState
from benchpro.core.domain.errors import TaskExecutionError, ResourceError, ExecutorError
from benchpro.core.executor.local.executor import LocalExecutor
from benchpro.core.services.settings import Settings

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get logger for this module
logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for each test."""
    # Set logging level for specific modules
    logging.getLogger('benchpro.core.executor.local.executor').setLevel(logging.DEBUG)
    logging.getLogger('benchpro.core.executor.local.process').setLevel(logging.DEBUG)
    logging.getLogger('benchpro.core.executor.local.resources').setLevel(logging.DEBUG)

@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.get.return_value = {
        "max_running_tasks": 2
    }
    return settings

@pytest.fixture
def local_executor(mock_settings):
    """Create a LocalExecutor instance."""
    return LocalExecutor(Path("/tmp"))

@pytest.fixture
def test_script():
    """Create a temporary test script file."""
    script_path = Path("/tmp/test_script.sh")
    script_path.write_text("#!/bin/bash\necho 'test'")
    script_path.chmod(0o755)
    yield script_path
    script_path.unlink(missing_ok=True)

def create_mock_task(test_script):
    """Create a mock task for testing."""
    task = MagicMock(spec=Task)
    task.id = str(uuid.uuid4())
    task.name = "test_task"
    task.working_dir = Path("/tmp")
    task.template_path = test_script
    task.variables = {"cores": 2, "memory": "4G"}
    task.state = TaskState.CREATED
    
    def transition_to(state):
        task.state = state
    task.transition_to = transition_to
    
    return task

@pytest.fixture
def mock_task(test_script):
    """Create a mock task for testing."""
    task = Task(
        name="test_task",
        working_dir=Path("/tmp/test"),
        template_path=test_script,
        variables={"cores": 2, "memory": "4G"},
        state=TaskState.CREATED
    )
    return task

@pytest.fixture
def mock_job():
    job = MagicMock(spec=Job)
    job.id = "test-job-1"
    job.name = "test-job"
    job.state = JobState.CREATED
    job.resources = {"cores": 1, "memory": "1G"}
    job.tasks = []  # Initialize tasks as empty list
    return job

@pytest.fixture
def mock_task():
    task = MagicMock(spec=Task)
    task.id = "test-task-1"
    task.name = "test-task"
    task.state = TaskState.PENDING
    task.working_dir = Path("/tmp/test")
    task.transition_to = lambda state: setattr(task, 'state', state)  # Add transition_to method
    return task

@pytest.mark.asyncio
async def test_validate_resources_success(local_executor, mock_job):
    """Test successful resource validation."""
    with patch("benchpro.core.executor.local.resources.ResourceManager.validate_resources", return_value=True):
        assert await local_executor.validate_resources(mock_job)

@pytest.mark.asyncio
async def test_validate_resources_failure(local_executor, mock_job):
    """Test resource validation failure."""
    with patch("benchpro.core.executor.local.resources.ResourceManager.validate_resources", return_value=False):
        assert not await local_executor.validate_resources(mock_job)

@pytest.mark.asyncio
async def test_submit_job_success(executor, tmp_path):
    """Test successful job submission."""
    # Create a simple test script
    script_path = tmp_path / "test_script.sh"
    script_path.write_text("#!/bin/sh\nexit 0\n")
    script_path.chmod(0o755)
    
    # Create task with real script
    task = Task(
        name="test-task",
        working_dir=tmp_path,
        template_path=script_path,
        variables={}
    )
    
    # Create job with the task
    job = Job(
        name="test-job",
        working_dir=tmp_path,
        tasks=[task],
        resources={"cores": 1, "memory": "1G"},
        state=JobState.CREATED
    )
    
    # Submit and verify
    await executor.submit_job(job)
    
    assert job.state == JobState.COMPLETED
    assert task.state == TaskState.COMPLETED

@pytest.mark.asyncio
async def test_submit_job_resource_validation_failure(executor, tmp_path):
    """Test job submission fails when resource validation fails."""
    # Create a simple test script
    script_path = tmp_path / "test_script.sh"
    script_path.write_text("#!/bin/sh\nexit 0\n")
    script_path.chmod(0o755)
    
    # Create task with real script
    task = Task(
        name="test-task",
        working_dir=tmp_path,
        template_path=script_path,
        variables={}
    )
    
    # Create job with the task
    job = Job(
        name="test-job",
        working_dir=tmp_path,
        tasks=[task],
        resources={"cores": 1, "memory": "1G"},
        state=JobState.CREATED
    )
    
    # Mock resource validation to fail and verify error handling
    with patch.object(executor._resource_manager, "validate_resources", return_value=False):
        # Submit job and expect it to fail
        with pytest.raises(ExecutorError) as excinfo:
            await executor.submit_job(job)
        
        # Verify the error and state changes
        assert str(excinfo.value) == "Resource validation failed"
        assert job.state == JobState.FAILED

@pytest.mark.asyncio
async def test_submit_job_task_failure(local_executor, mock_job, mock_task):
    """Test job submission with task failure."""
    assert mock_job.state == JobState.CREATED
    error_msg = "Task failed with exit code 1: error message"
    
    # Add task to job
    mock_job.tasks = [mock_task]
    
    with patch("benchpro.core.executor.local.resources.ResourceManager.validate_resources", return_value=True), \
         patch("benchpro.core.executor.local.process.ProcessManager.execute_task", side_effect=TaskExecutionError(error_msg)):
        with pytest.raises(TaskExecutionError) as exc_info:
            await local_executor.submit_job(mock_job)
        assert exc_info.value.message == error_msg
            
    assert mock_job.state == JobState.FAILED
    assert mock_job.tasks[0].state == TaskState.FAILED

@pytest.mark.asyncio
async def test_submit_job_cancellation(local_executor, mock_job):
    """Test job submission with cancellation."""
    assert mock_job.state == JobState.CREATED
    with patch("benchpro.core.executor.local.resources.ResourceManager.validate_resources", return_value=True), \
         patch("benchpro.core.executor.local.process.ProcessManager.execute_task", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await local_executor.submit_job(mock_job)
            
    assert mock_job.state == JobState.CANCELLED
    assert mock_job.tasks[0].state == TaskState.CANCELLED

@pytest.mark.asyncio
async def test_cancel_job(local_executor, mock_job):
    """Test job cancellation."""
    assert mock_job.state == JobState.CREATED
    with patch("benchpro.core.executor.local.process.ProcessManager.cancel_job") as mock_cancel:
        await local_executor.cancel_job(mock_job)
        mock_cancel.assert_called_once_with(mock_job)
        assert mock_job.state == JobState.CANCELLED

@pytest.mark.asyncio
async def test_cancel_job_failure(local_executor, mock_job):
    """Test job cancellation failure."""
    error_msg = "Cancel failed"
    expected_error = f"Failed to cancel job: {error_msg}"
    with patch("benchpro.core.executor.local.process.ProcessManager.cancel_job", side_effect=Exception(error_msg)):
        with pytest.raises(ExecutorError) as exc_info:
            await local_executor.cancel_job(mock_job)
        assert exc_info.value.message == expected_error
        assert mock_job.state == JobState.CREATED

@pytest.mark.asyncio
async def test_get_job_status(local_executor, mock_job):
    """Test getting job status."""
    assert mock_job.state == JobState.CREATED
    result = await local_executor.get_job_status(mock_job)

    assert result["job_id"] == str(mock_job.id)
    assert result["state"] == JobState.CREATED.value

@pytest.mark.asyncio
async def test_get_job_status_failure(local_executor, mock_job):
    """Test job status retrieval failure."""
    mock_job.tasks = []
    local_executor._jobs[mock_job.id] = mock_job
    
    # Force an error by making tasks raise an exception when accessed
    mock_job.tasks = property(lambda _: (_ for _ in ()).throw(Exception("Failed to get tasks")))
    
    with pytest.raises(ExecutorError) as exc_info:
        await local_executor.get_job_status(mock_job)
        
    assert exc_info.value.message == "Failed to get job status"

@pytest.mark.asyncio
async def test_get_resource_usage_no_process(local_executor, mock_job):
    """Test getting resource usage with no process."""
    with patch("benchpro.core.executor.local.process.ProcessManager.get_process", return_value=None):
        usage = await local_executor.get_resource_usage(mock_job)
        
    assert usage["cores"] == mock_job.resources["cores"]
    assert usage["memory"] == mock_job.resources["memory"]

@pytest.mark.asyncio
async def test_get_resource_usage_mock_process(local_executor, mock_job):
    """Test getting resource usage with mock process."""
    mock_process = AsyncMock()
    mock_process.pid = AsyncMock()
    
    with patch("benchpro.core.executor.local.process.ProcessManager.get_process", return_value=mock_process):
        usage = await local_executor.get_resource_usage(mock_job)
        
    assert usage["cores"] == mock_job.resources["cores"]
    assert usage["memory"] == mock_job.resources["memory"]

@pytest.mark.asyncio
async def test_get_resource_usage_failure(local_executor, mock_job):
    """Test resource usage retrieval failure."""
    mock_job.tasks = []
    executor._jobs[mock_job.id] = mock_job
    
    # Force resources to raise an exception when accessed
    mock_job.resources = property(lambda _: (_ for _ in ()).throw(Exception("Failed to get resources")))
    
    with pytest.raises(ExecutorError) as exc_info:
        await local_executor.get_resource_usage(mock_job)
        
    assert exc_info.value.message == "Failed to get resource usage"

@pytest.fixture
def executor():
    return LocalExecutor(Path("/tmp/test"))

@pytest.mark.asyncio
async def test_validate_resources_success(executor, mock_job, mock_task):
    """Test resource validation succeeds."""
    mock_job.tasks = [mock_task]
    
    # Mock resource validation to succeed
    with patch.object(executor._resource_manager, "validate_resources", return_value=True):
        result = await executor.validate_resources(mock_job)
        assert result is True

@pytest.mark.asyncio
async def test_validate_resources_failure(executor, mock_job, mock_task):
    """Test resource validation fails."""
    mock_job.tasks = [mock_task]
    
    # Mock resource validation to fail
    with patch.object(executor._resource_manager, "validate_resources", return_value=False):
        result = await executor.validate_resources(mock_job)
        assert result is False

@pytest.mark.asyncio
async def test_submit_job_task_execution_failure(executor, mock_job, mock_task):
    """Test job submission fails when task execution fails."""
    mock_job.tasks = [mock_task]
    
    # Mock resource validation to pass but task execution to fail
    with patch.object(executor, "validate_resources", return_value=True):
        with patch.object(executor._process_manager, "execute_task", 
                         side_effect=TaskExecutionError("Task execution failed")):
            with pytest.raises(TaskExecutionError) as exc_info:
                await executor.submit_job(mock_job)
                
            assert exc_info.value.message == "Task execution failed"
            assert mock_job.state == JobState.FAILED
            assert mock_task.state == TaskState.FAILED

@pytest.mark.asyncio
async def test_submit_job_cancellation(executor, mock_job, mock_task):
    """Test job submission handles cancellation."""
    mock_job.tasks = [mock_task]
    
    # Mock resource validation to pass but task execution to be cancelled
    with patch.object(executor, "validate_resources", return_value=True):
        with patch.object(executor._process_manager, "execute_task", 
                         side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await executor.submit_job(mock_job)
                
            assert mock_job.state == JobState.CANCELLED
            assert mock_task.state == TaskState.CANCELLED

@pytest.mark.asyncio
async def test_cancel_job(executor, mock_job):
    """Test successful job cancellation."""
    mock_job.tasks = []
    executor._jobs[mock_job.id] = mock_job
    
    # Mock process manager to succeed
    with patch.object(executor._process_manager, "cancel_job"):
        await executor.cancel_job(mock_job)
        assert mock_job.state == JobState.CANCELLED

@pytest.mark.asyncio
async def test_cancel_job_failure(executor, mock_job):
    """Test job cancellation failure."""
    mock_job.tasks = []
    executor._jobs[mock_job.id] = mock_job
    
    # Mock process manager to fail cancellation
    with patch.object(executor._process_manager, "cancel_job",
                     side_effect=Exception("Failed to cancel")):
        with pytest.raises(ExecutorError) as exc_info:
            await executor.cancel_job(mock_job)
            
        assert exc_info.value.message == "Failed to cancel job: Failed to cancel"
        assert mock_job.state != JobState.CANCELLED  # State should not change on failure

@pytest.mark.asyncio
async def test_get_job_status(executor, mock_job, mock_task):
    """Test successful job status retrieval."""
    mock_job.tasks = [mock_task]
    executor._jobs[mock_job.id] = mock_job
    
    status = await executor.get_job_status(mock_job)
    assert status["job_id"] == mock_job.id
    assert status["state"] == mock_job.state.value
    assert status["tasks"]["total"] == 1

@pytest.mark.asyncio
async def test_get_resource_usage_failure(executor, mock_job):
    """Test resource usage retrieval failure."""
    mock_job.tasks = []
    executor._jobs[mock_job.id] = mock_job
    
    # Force resources to raise an exception when accessed
    mock_job.resources = property(lambda _: (_ for _ in ()).throw(Exception("Failed to get resources")))
    
    with pytest.raises(ExecutorError) as exc_info:
        await executor.get_resource_usage(mock_job)
        
    assert exc_info.value.message == "Failed to get resource usage"

@pytest.mark.asyncio
async def test_cleanup_job_failure(executor, mock_job, mock_task):
    """Test job cleanup failure."""
    mock_job.tasks = [mock_task]
    executor._jobs[mock_job.id] = mock_job
    
    # Mock process manager to fail cleanup
    with patch.object(executor._process_manager, "cleanup_job",
                     side_effect=Exception("Failed to clean up")):
        with pytest.raises(ExecutorError) as exc_info:
            await executor.cleanup_job(mock_job)
            
        assert exc_info.value.message == "Failed to clean up job: Failed to clean up"