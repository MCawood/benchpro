import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from benchpro.core.services.capture import CaptureService
from benchpro.core.domain import Task, TaskStatus, ResourceRequest
from benchpro.core.config import Config, SystemConfig

@pytest.fixture
def mock_config():
    config = Mock(spec=Config)
    config.system = Mock(spec=SystemConfig)
    config.system.name = "test_system"
    config.system.results_server_url = "http://test-server"
    config.system.api_token = "test_token"
    return config

@pytest.fixture
def mock_store():
    return Mock()

@pytest.fixture
def capture_service(mock_store, mock_config):
    return CaptureService(result_store=mock_store, config=mock_config)

@pytest.fixture
def sample_task(tmp_path):
    # Create a dummy working directory
    work_dir = tmp_path / "work_dir"
    work_dir.mkdir()
    
    # Create a dummy output file
    (work_dir / "slurm-123.out").write_text("Result: 100 GFLOPS")
    
    return Task(
        task_id="test_task",
        suite_id="test_suite",
        command="echo hello",
        resources=ResourceRequest(nodes=1),
        status=TaskStatus.COMPLETED,
        job_id="123",
        working_directory=str(work_dir),
        task_uuid="uuid-123",
        duration_ms=1000
    )

def test_generate_payload(capture_service, sample_task):
    metrics = {"gflops": {"value": 100.0, "unit": "GFLOPS"}}
    work_dir = Path(sample_task.working_directory)
    
    payload = capture_service._generate_payload(sample_task, metrics, work_dir)
    
    assert payload["client"]["task_uuid"] == "uuid-123"
    assert payload["task"]["label"] == "test_task"
    assert payload["task"]["system"] == "test_system"
    assert len(payload["figures_of_merit"]) == 1
    assert payload["figures_of_merit"][0]["name"] == "gflops"
    assert payload["figures_of_merit"][0]["value_numeric"] == 100.0
    
    # Check artifacts
    assert len(payload["provenance"]["artifacts"]) == 1
    assert payload["provenance"]["artifacts"][0]["name"] == "slurm-123.out"

@patch("benchpro.core.services.capture.httpx.post")
def test_submit_result_success(mock_post, capture_service):
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"task_run_id": 456, "duplicate": False}
    mock_post.return_value = mock_response
    
    payload = {"test": "data"}
    capture_service.submit_result(payload)
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["json"] == payload
    assert kwargs["headers"]["Authorization"] == "Bearer test_token"

@patch("benchpro.core.services.capture.httpx.post")
def test_submit_result_failure(mock_post, capture_service):
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server Error"
    mock_response.raise_for_status.side_effect = Exception("Server Error")
    mock_post.return_value = mock_response
    
    with pytest.raises(Exception):
        capture_service.submit_result({})

@patch("benchpro.core.services.capture.ResultParser.parse")
def test_capture_result_flow(mock_parse, capture_service, sample_task):
    mock_parse.return_value = {"gflops": {"value": 100.0, "unit": "GFLOPS"}}
    
    with patch.object(capture_service, "submit_result") as mock_submit:
        capture_service.capture_result(sample_task)
        
        # Check if metrics were saved
        capture_service.result_store.save_metrics.assert_called_once()
        
        # Check if submission was called
        mock_submit.assert_called_once()
        
        # Check if submission file was created
        work_dir = Path(sample_task.working_directory)
        assert (work_dir / "submission.json").exists()
