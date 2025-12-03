import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from benchpro.core.domain import Task, TaskStatus, ResourceRequest
from benchpro.core.services.capture import CaptureService

@pytest.fixture
def mock_store():
    return Mock()

@pytest.fixture
def service(mock_store):
    return CaptureService(result_store=mock_store)

@pytest.fixture
def sample_task():
    return Task(
        task_id="test_task",
        suite_id="test_suite",
        resources=ResourceRequest(),
        command="echo hello",
        status=TaskStatus.RUNNING,
        job_id="12345",
        working_directory="/tmp/test_dir",
        task_uuid="uuid-123"
    )

def test_check_task_status_completed(service, sample_task):
    # Mock Slurm backend
    service.slurm.query_job_status = Mock(return_value={"12345": "COMPLETED"})
    
    status = service.check_task_status(sample_task)
    
    assert status == TaskStatus.COMPLETED
    assert sample_task.status == TaskStatus.COMPLETED
    service.result_store.save_task.assert_called_once()

def test_check_task_status_running(service, sample_task):
    service.slurm.query_job_status = Mock(return_value={"12345": "RUNNING"})
    
    status = service.check_task_status(sample_task)
    
    assert status == TaskStatus.RUNNING
    assert sample_task.status == TaskStatus.RUNNING
    # Should not save if status didn't change
    service.result_store.save_task.assert_not_called()

def test_capture_result_no_workdir(service, sample_task):
    sample_task.status = TaskStatus.COMPLETED
    sample_task.working_directory = None
    
    service.capture_result(sample_task)
    # Should just return/print error, no exception
    # Verify no metrics saved
    service.result_store.save_metrics.assert_not_called()

@patch("benchpro.core.services.capture.ResultParser")
@patch("pathlib.Path.exists")
@patch("pathlib.Path.glob")
def test_capture_result_success(mock_glob, mock_exists, mock_parser, service, sample_task):
    sample_task.status = TaskStatus.COMPLETED
    mock_exists.return_value = True
    
    # Mock output file
    mock_file = MagicMock()
    mock_file.stat.return_value.st_mtime = 100
    mock_file.stat.return_value.st_size = 100
    mock_file.name = "slurm-12345.out"
    mock_glob.return_value = [mock_file]
    
    # Mock parser
    mock_parser.parse.return_value = {"metric1": {"value": 10.0, "unit": "s"}}
    
    # Mock open for payload writing
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        service.capture_result(sample_task)
        
        service.result_store.save_metrics.assert_called_once()
        mock_open.assert_called() # Should write payload
