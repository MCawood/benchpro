import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock
from benchpro.core.domain.states import TaskState, JobState

@pytest.fixture
def create_mock_task():
    """Create a mock task with a real template file."""
    temp_dir = tempfile.mkdtemp()
    template_path = Path(temp_dir) / "test_script.sh"
    
    # Create a simple bash script
    with open(template_path, "w") as f:
        f.write("#!/bin/bash\necho 'test'")
    
    # Make it executable
    os.chmod(template_path, 0o755)
    
    task = MagicMock()
    task.id = "test_task_id"
    task.name = "test_task"
    task.working_dir = Path("/tmp")
    task.template_path = template_path
    task.variables = {"cores": 2, "memory": "4G"}
    task.state = TaskState.CREATED
    return task

@pytest.fixture
def mock_task(create_mock_task):
    """Return a mock task."""
    return create_mock_task()

@pytest.fixture
def mock_job(mock_task):
    """Return a mock job containing the mock task."""
    from benchpro.core.domain.job import Job
    
    job = Job(
        name="test_job",
        working_dir=Path("/"),
        tasks=[mock_task],
        resources={"cores": 2, "memory": "4G"}
    )
    job.state = JobState.CREATED
    return job 