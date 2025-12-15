import os
import pytest
import shutil
from typing import List, Dict
from pathlib import Path
from click.testing import CliRunner
from benchpro.core.config import Config
from benchpro.core.results import ResultStore
from benchpro.core.scheduler import SchedulerBackend
from benchpro.core.domain import Job

# --- Mock Backend ---
class MockSchedulerBackend(SchedulerBackend):
    def __init__(self):
        self.jobs = []
        self.cancelled_jobs = []

    def submit_job(self, job: Job) -> str:
        job_id = f"mock_job_{len(self.jobs)}"
        self.jobs.append((job_id, job))
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        self.cancelled_jobs.append(job_id)
        return True

    def query_job_status(self, job_ids: List[str]) -> Dict[str, str]:
        return {jid: "completed" for jid in job_ids}

    def wait_for_jobs(self, job_ids: List[str], timeout: int = 60, poll_interval: int = 2) -> bool:
        return True

# --- Fixtures ---

@pytest.fixture
def workspace(tmp_path):
    """
    Creates an isolated workspace for testing.
    Sets BENCHPRO_CONFIG and BENCHPRO_HOME env vars.
    """
    home = tmp_path / "benchpro_home"
    home.mkdir()
    
    config_dir = home / ".benchpro"
    config_dir.mkdir()
    
    # Create a minimal config
    config_path = config_dir / "config.yaml"
    with open(config_path, "w") as f:
        f.write("""
system:
  name: test_system
  max_local_tasks: 2
defaults:
  output_dir: ${env.BENCHPRO_HOME}/results
""")
    
    # Set env vars
    os.environ["BENCHPRO_HOME"] = str(home)
    # Config loading looks in CWD/.benchpro, HOME/.config/benchpro, etc.
    # We can force a path by mocking Config.load or setting an env var if supported.
    # The current Config.load implementation checks specific paths.
    # To make it testable without patching, we should probably allow an env var override 
    # or just rely on the fact that we can pass paths to Config.load.
    # However, for CLI tests, we need it to pick up the config.
    # Let's assume we'll patch Config.load or use a context manager in tests.
    
    return home

@pytest.fixture
def mock_scheduler():
    return MockSchedulerBackend()

@pytest.fixture
def result_store(workspace):
    db_path = workspace / "results.db"
    return ResultStore(db_path=db_path)

@pytest.fixture
def runner():
    return CliRunner()
