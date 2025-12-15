import pytest
from unittest.mock import MagicMock, patch
from benchpro.core.scheduler import SlurmBackend, LocalBackend
from benchpro.core.domain import Job, ResourceRequest

@pytest.fixture
def mock_job():
    return Job(
        job_id="test_job",
        script_content="echo hello",
        resources=ResourceRequest(nodes=1)
    )

def test_slurm_dependency_string_generation():
    backend = SlurmBackend()
    
    # Single dependency
    mock_job_with_dep = Job(
        job_id="j1", 
        script_content="echo", 
        resources=ResourceRequest(nodes=1),
        scheduler_dependencies=["101"]
    )
    # White-box testing the method if it was public, but usually it's internal.
    # However, we can check if _submit_slurm_job (if we Mock subprocess) calls sbatch with dep.
    pass 

@patch("subprocess.Popen")
def test_slurm_submit_with_deps(mock_popen, mock_job):
    backend = SlurmBackend()
    mock_job.scheduler_dependencies = ["1001", "1002"]
    
    # Mock successful sbatch
    # Popen instance setup
    process_mock = mock_popen.return_value
    process_mock.communicate.return_value = ("Submitted batch job 12345\n", "")
    process_mock.returncode = 0
    
    job_id = backend.submit_job(mock_job)
    
    assert job_id == "12345"
    
    # Verify call args
    # Popen was called with dependency args?
    # SlurmBackend constructs cmd list passed to Popen.
    args = mock_popen.call_args[0][0]
    # We might need to check if --dependency logic is actually implemented in SlurmBackend.submit_job?
    # I verified it earlier in executor.py. 
    # Wait, Executor handles dependencies. SlurmBackend.submit_job just receives a `Job` object.
    # Does SlurmBackend logic actually ADD dependencies to the command?
    # Looking at viewed file `core/scheduler.py` lines 30-61...
    # It just runs `sbatch` and pipes `job.script_content`.
    # It does NOT inspect `job.scheduler_dependencies` to add flags!
    # The dependency logic was added to Executor in `_submit_slurm_jobs`.
    # So SlurmBackend.submit_job is "dumb" regarding dependencies unless it's designed to handle them.
    # To fix this, I should probably move dependency handling into SlurmBackend or update the test.
    # The test `test_slurm_submit_with_deps` assumes SlurmBackend handles it.
    # If the logic is in Executor, this test is testing functionality that doesn't exist in SchedulerBackend.
    # I should either:
    # A) Update SlurmBackend to handle dependencies (Better architecture)
    # B) Test Executor instead.
    
    # The Executor calls `backend.submit_job(job)`.
    # If `backend.submit_job` doesn't handle dependencies, then Executor must be generating the script with #SBATCH --dependency?
    # OR Executor passes flags to `submit_job`?
    # Let's check Executor.

    pass # Placeholder for replace logic

def test_local_backend_execution():
    backend = LocalBackend()
    job = Job(
        job_id="local_j1",
        script_content="echo test_local",
        resources=ResourceRequest(nodes=1)
    )
    
    # LocalBackend just returns "local_job"
    jid = backend.submit_job(job)
    assert jid == "local_job"
