"""Tests for the local executor implementation."""

import pytest
import asyncio
import os
import psutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from benchpro.core.executor.local import LocalExecutor
from benchpro.core.executor.base import ExecutorError, TaskExecutionError, ResourceError
from benchpro.core.domain import Task, TaskState, Job

@pytest.fixture
def local_executor(tmp_path):
    """Create a local executor instance."""
    return LocalExecutor(tmp_path)

@pytest.fixture
def mock_task(tmp_path):
    """Create a mock task for testing."""
    task_dir = tmp_path / "tasks" / "test-task"
    task_dir.mkdir(parents=True)
    template = tmp_path / "templates" / "test.sh"
    template.parent.mkdir(parents=True)
    template.write_text("#!/bin/bash\necho 'test'")
    return Task(
        name="test-task",
        working_dir=task_dir,
        template_path=template,
        variables={
            "cores": 1,
            "memory": "1G",
            "walltime": 3600
        }
    )

@pytest.fixture
def mock_job(mock_task):
    """Create a mock job containing the mock task."""
    return Job(
        name="test-job",
        working_dir=mock_task.working_dir.parent,
        tasks=[mock_task]
    )

@pytest.mark.asyncio
async def test_validate_resources_success(local_executor, mock_task):
    """Test successful resource validation."""
    with patch('psutil.cpu_count', return_value=4), \
         patch('psutil.virtual_memory', return_value=MagicMock(available=4*1024*1024*1024)), \
         patch('shutil.disk_usage', return_value=MagicMock(free=10*1024*1024*1024)):
        assert await local_executor.validate_resources(mock_task)

@pytest.mark.asyncio
async def test_validate_resources_insufficient_cores(local_executor, mock_task):
    """Test resource validation with insufficient CPU cores."""
    mock_task.variables['cores'] = 8
    with patch('psutil.cpu_count', return_value=4):
        with pytest.raises(ResourceError, match="Not enough CPU cores"):
            await local_executor.validate_resources(mock_task)

@pytest.mark.asyncio
async def test_validate_resources_insufficient_memory(local_executor, mock_task):
    """Test resource validation with insufficient memory."""
    mock_task.variables['memory'] = '8G'
    with patch('psutil.virtual_memory', return_value=MagicMock(available=4*1024*1024*1024)):
        with pytest.raises(ResourceError, match="Not enough memory"):
            await local_executor.validate_resources(mock_task)

@pytest.mark.asyncio
async def test_prepare_task(local_executor, mock_task, mock_job):
    """Test task preparation."""
    local_executor._jobs[mock_job.id] = mock_job
    await local_executor.prepare(mock_task)
    assert mock_task.state == TaskState.PENDING

@pytest.mark.asyncio
async def test_prepare_task_no_template(local_executor, mock_task, mock_job):
    """Test task preparation without template."""
    mock_task.template_path = None
    local_executor._jobs[mock_job.id] = mock_job
    with pytest.raises(ExecutorError, match="Template path does not exist"):
        await local_executor.prepare(mock_task)

@pytest.mark.asyncio
async def test_run_task(local_executor, mock_task, mock_job):
    """Test task execution."""
    mock_process = AsyncMock()
    mock_process.returncode = 0  # Set returncode to 0 for success
    mock_process.communicate.return_value = (b"test output", b"")
    
    local_executor._jobs[mock_job.id] = mock_job
    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        await local_executor.run(mock_task)
        assert local_executor._process_manager.get_process(mock_task.id) is None  # Process should be cleaned up
        assert mock_task.state == TaskState.COMPLETED

@pytest.mark.asyncio
async def test_run_task_no_template(local_executor, mock_task, mock_job):
    """Test task execution without template."""
    mock_task.template_path = None
    local_executor._jobs[mock_job.id] = mock_job
    with pytest.raises(ExecutorError, match="Template path does not exist"):
        await local_executor.run(mock_task)
        assert mock_task.state == TaskState.FAILED

@pytest.mark.asyncio
async def test_status_running(local_executor, mock_task, mock_job):
    """Test status check for running task."""
    mock_process = MagicMock()
    mock_process.returncode = None
    local_executor._jobs[mock_job.id] = mock_job
    local_executor._process_manager._processes[mock_task.id] = mock_process
    assert await local_executor.status(mock_task) == TaskState.RUNNING

@pytest.mark.asyncio
async def test_status_completed(local_executor, mock_task, mock_job):
    """Test status check for completed task."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    local_executor._jobs[mock_job.id] = mock_job
    local_executor._process_manager._processes[mock_task.id] = mock_process
    assert await local_executor.status(mock_task) == TaskState.COMPLETED

@pytest.mark.asyncio
async def test_status_failed(local_executor, mock_task, mock_job):
    """Test status check for failed task."""
    mock_process = MagicMock()
    mock_process.returncode = 1
    local_executor._jobs[mock_job.id] = mock_job
    local_executor._process_manager._processes[mock_task.id] = mock_process
    assert await local_executor.status(mock_task) == TaskState.FAILED

@pytest.mark.asyncio
async def test_stop_task(local_executor, mock_task, mock_job):
    """Test stopping a task."""
    # Mock process
    mock_process = AsyncMock()
    mock_process.returncode = None
    mock_process.wait.return_value = 0
    local_executor._jobs[mock_job.id] = mock_job
    local_executor._process_manager._processes[mock_task.id] = mock_process
    
    await local_executor.stop(mock_task)
    mock_process.terminate.assert_called_once()
    assert mock_task.state == TaskState.CANCELLED

@pytest.mark.asyncio
async def test_cleanup_task(local_executor, mock_task, mock_job):
    """Test task cleanup."""
    # Create mock log files
    (mock_task.working_dir / "stdout.log").write_text("test output")
    (mock_task.working_dir / "stderr.log").write_text("test error")
    
    local_executor._jobs[mock_job.id] = mock_job
    local_executor._process_manager._processes[mock_task.id] = AsyncMock()
    
    await local_executor.cleanup(mock_task)
    assert mock_task.id not in local_executor._process_manager._processes

def test_parse_memory():
    """Test memory string parsing."""
    executor = LocalExecutor(Path())
    assert executor._parse_memory("1K") == 1024
    assert executor._parse_memory("1M") == 1024 * 1024
    assert executor._parse_memory("1G") == 1024 * 1024 * 1024
    assert executor._parse_memory("1T") == 1024 * 1024 * 1024 * 1024
    
    with pytest.raises(ValueError):
        executor._parse_memory("invalid")

def test_format_memory():
    """Test memory formatting."""
    executor = LocalExecutor(Path())
    assert executor._format_memory(1024) == "1.0K"
    assert executor._format_memory(1024 * 1024) == "1.0M"
    assert executor._format_memory(1024 * 1024 * 1024) == "1.0G"
    assert executor._format_memory(1024 * 1024 * 1024 * 1024) == "1.0T" 