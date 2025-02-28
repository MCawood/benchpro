"""
Tests for the Executor classes.
"""

import os
import pytest
import tempfile
import time
from benchpro.executor.executor import Executor, LocalExecutor, SchedulerExecutor


def test_executor_factory():
    """Test the Executor factory method."""
    local_executor = Executor.get_executor("local")
    assert isinstance(local_executor, LocalExecutor)
    
    scheduler_executor = Executor.get_executor("scheduler")
    assert isinstance(scheduler_executor, SchedulerExecutor)
    
    with pytest.raises(ValueError):
        Executor.get_executor("invalid_type")


def test_local_executor():
    """Test the LocalExecutor."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple script
        script_path = os.path.join(temp_dir, "test_script.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\necho 'Hello, World!'\nsleep 1\n")
        
        # Make it executable
        os.chmod(script_path, 0o755)
        
        # Create a local executor
        executor = LocalExecutor()
        
        # Submit the job
        success, job_id = executor.submit_job(script_path)
        
        # Check that the job was submitted successfully
        assert success
        assert job_id is not None
        
        # Check the status (might be RUNNING or COMPLETED depending on timing)
        status = executor.check_status(job_id)
        assert status in ["RUNNING", "COMPLETED"]
        
        # Wait for the job to complete
        time.sleep(2)
        
        # Check the status again
        status = executor.check_status(job_id)
        assert status == "COMPLETED"


def test_local_executor_with_error():
    """Test the LocalExecutor with a script that fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a script that will fail
        script_path = os.path.join(temp_dir, "failing_script.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\nexit 1\n")
        
        # Make it executable
        os.chmod(script_path, 0o755)
        
        # Create a local executor
        executor = LocalExecutor()
        
        # Submit the job
        success, job_id = executor.submit_job(script_path)
        
        # Check that the job was submitted successfully
        assert success
        assert job_id is not None
        
        # Wait for the job to complete
        time.sleep(1)
        
        # Check the status
        # Note: In our simplified implementation, we can't distinguish between successful
        # and failed completions without additional tracking
        status = executor.check_status(job_id)
        assert status == "COMPLETED"


def test_scheduler_executor_mock(monkeypatch):
    """Test the SchedulerExecutor with mocked scheduler."""
    # Mock the get_scheduler function
    class MockScheduler:
        def submit_job(self, script_path, context=None):
            return "12345"
        
        def check_status(self, job_id):
            return "RUNNING"
        
        def cancel_job(self, job_id):
            return True
    
    def mock_get_scheduler(scheduler_type, config=None):
        return MockScheduler()
    
    monkeypatch.setattr("benchpro.executor.executor.get_scheduler", mock_get_scheduler)
    
    # Create a scheduler executor
    executor = SchedulerExecutor({"type": "slurm"})
    
    # Submit a job
    success, job_id = executor.submit_job("dummy_script.sh")
    
    # Check that the job was submitted successfully
    assert success
    assert job_id == "12345"
    
    # Check the status
    status = executor.check_status(job_id)
    assert status == "RUNNING"
    
    # Cancel the job
    result = executor.cancel_job(job_id)
    assert result is True 