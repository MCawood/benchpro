import pytest
from benchpro.core.domain import Job
from benchpro.core.scheduler import SlurmBackend

def test_slurm_submit_mock(mock_scheduler):
    # We can't easily test the real SlurmBackend without sbatch
    # But we can test that our MockSchedulerBackend works as expected
    job = Job(job_id="test_job", script_content="#!/bin/bash\necho hello")
    job_id = mock_scheduler.submit_job(job)
    assert job_id.startswith("mock_job_")
    assert len(mock_scheduler.jobs) == 1

def test_slurm_backend_script_generation():
    # We could test the _submit_slurm_task logic in Executor here
    # but that's better in test_executor.py
    pass
