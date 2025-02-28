"""Tests for the ResourceManager class."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import uuid

from benchpro.core.domain import Task, Job, TaskState, JobState
from benchpro.core.executor.base import ResourceError
from benchpro.core.executor.local.resources import ResourceManager

@pytest.fixture
def resource_manager():
    """Create a ResourceManager instance."""
    return ResourceManager(Path("/tmp"))

def create_mock_task():
    """Create a mock task for testing."""
    task = MagicMock(spec=Task)
    task.id = str(uuid.uuid4())
    task.name = "test_task"
    task.working_dir = Path("/tmp")
    task.template_path = Path("/tmp/test_script.sh")
    task.variables = {"cores": 2, "memory": "4G", "disk_space": 1024 * 1024 * 1024}  # 1GB
    task.state = TaskState.CREATED
    return task

@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    return create_mock_task()

@pytest.fixture
def mock_job():
    """Create a mock job for testing."""
    task = create_mock_task()
    job = Job(
        name="test_job",
        working_dir=Path("/"),
        tasks=[task],
        resources={"cores": 2, "memory": "4G", "disk_space": 1024 * 1024 * 1024},  # 1GB
        state=JobState.CREATED
    )
    return job

def test_parse_memory(resource_manager):
    """Test memory string parsing."""
    assert resource_manager._parse_memory("1K") == 1024
    assert resource_manager._parse_memory("1M") == 1024 * 1024
    assert resource_manager._parse_memory("1G") == 1024 * 1024 * 1024
    assert resource_manager._parse_memory("1T") == 1024 * 1024 * 1024 * 1024
    assert resource_manager._parse_memory("1024") == 1024
    assert resource_manager._parse_memory("2.5G") == int(2.5 * 1024 * 1024 * 1024)

def test_format_memory(resource_manager):
    """Test memory formatting."""
    assert resource_manager._format_memory(1024) == "1.0K"
    assert resource_manager._format_memory(1024 * 1024) == "1.0M"
    assert resource_manager._format_memory(1024 * 1024 * 1024) == "1.0G"
    assert resource_manager._format_memory(1024 * 1024 * 1024 * 1024) == "1.0T"

@pytest.mark.asyncio
async def test_validate_resources_task_success(resource_manager, mock_task):
    """Test successful resource validation for a task."""
    mock_task.resources = {"cores": 2, "memory": "4G"}  # Add resources to mock task
    
    mock_cpu = MagicMock()
    mock_cpu.return_value = 4  # 4 cores available

    mock_memory = MagicMock()
    mock_memory.available = 8 * 1024 * 1024 * 1024  # 8GB available

    mock_disk = MagicMock()
    mock_disk.free = 10 * 1024 * 1024 * 1024  # 10GB available

    with patch("psutil.cpu_count", mock_cpu), \
         patch("psutil.virtual_memory", return_value=mock_memory), \
         patch("psutil.disk_usage", return_value=mock_disk):
        assert await resource_manager.validate_resources(mock_task)

@pytest.mark.asyncio
async def test_validate_resources_job_success(resource_manager, mock_job):
    """Test successful resource validation for a job."""
    mock_cpu = MagicMock()
    mock_cpu.return_value = 4  # 4 cores available
    
    mock_memory = MagicMock()
    mock_memory.available = 8 * 1024 * 1024 * 1024  # 8GB available
    
    mock_disk = MagicMock()
    mock_disk.free = 10 * 1024 * 1024 * 1024  # 10GB available
    
    with patch("psutil.cpu_count", mock_cpu), \
         patch("psutil.virtual_memory", return_value=mock_memory), \
         patch("psutil.disk_usage", return_value=mock_disk):
        assert await resource_manager.validate_resources(mock_job)

@pytest.mark.asyncio
async def test_validate_resources_insufficient_cores(resource_manager, mock_job):
    """Test resource validation with insufficient CPU cores."""
    mock_job.resources["cores"] = 8  # Request 8 cores
    
    mock_cpu = MagicMock()
    mock_cpu.return_value = 4  # Only 4 cores available
    
    mock_memory = MagicMock()
    mock_memory.available = 8 * 1024 * 1024 * 1024  # 8GB available
    
    mock_disk = MagicMock()
    mock_disk.free = 10 * 1024 * 1024 * 1024  # 10GB available
    
    with patch("psutil.cpu_count", mock_cpu), \
         patch("psutil.virtual_memory", return_value=mock_memory), \
         patch("psutil.disk_usage", return_value=mock_disk):
        assert not await resource_manager.validate_resources(mock_job)

@pytest.mark.asyncio
async def test_validate_resources_insufficient_memory(resource_manager, mock_job):
    """Test resource validation with insufficient memory."""
    mock_job.resources["memory"] = "16G"  # Request 16GB
    
    mock_cpu = MagicMock()
    mock_cpu.return_value = 4  # 4 cores available
    
    mock_memory = MagicMock()
    mock_memory.available = 8 * 1024 * 1024 * 1024  # Only 8GB available
    
    mock_disk = MagicMock()
    mock_disk.free = 10 * 1024 * 1024 * 1024  # 10GB available
    
    with patch("psutil.cpu_count", mock_cpu), \
         patch("psutil.virtual_memory", return_value=mock_memory), \
         patch("psutil.disk_usage", return_value=mock_disk):
        assert not await resource_manager.validate_resources(mock_job)

@pytest.mark.asyncio
async def test_validate_resources_insufficient_disk(resource_manager, mock_job):
    """Test resource validation with insufficient disk space."""
    mock_job.resources["disk_space"] = 20 * 1024 * 1024 * 1024  # Request 20GB
    
    mock_cpu = MagicMock()
    mock_cpu.return_value = 4  # 4 cores available
    
    mock_memory = MagicMock()
    mock_memory.available = 8 * 1024 * 1024 * 1024  # 8GB available
    
    mock_disk = MagicMock()
    mock_disk.free = 10 * 1024 * 1024 * 1024  # Only 10GB available
    
    with patch("psutil.cpu_count", mock_cpu), \
         patch("psutil.virtual_memory", return_value=mock_memory), \
         patch("psutil.disk_usage", return_value=mock_disk):
        assert not await resource_manager.validate_resources(mock_job)

def test_get_resource_usage(resource_manager):
    """Test getting resource usage for a process."""
    mock_process = MagicMock()
    mock_process.cpu_percent.return_value = 50.0
    mock_process.memory_percent.return_value = 25.0
    mock_memory_info = MagicMock()
    mock_memory_info.rss = 1024 * 1024 * 100  # 100MB
    mock_memory_info.vms = 1024 * 1024 * 200  # 200MB
    mock_process.memory_info.return_value = mock_memory_info
    
    usage = resource_manager.get_resource_usage(mock_process)
    
    assert usage["cpu_percent"] == 50.0
    assert usage["memory_percent"] == 25.0
    assert usage["memory_rss"] == float(1024 * 1024 * 100)
    assert usage["memory_vms"] == float(1024 * 1024 * 200) 