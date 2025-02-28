"""Pytest fixtures for Slurm simulator testing."""

import pytest
from pathlib import Path
from . import SlurmSimulator

@pytest.fixture
def slurm_simulator():
    """Create a SlurmSimulator instance."""
    simulator = SlurmSimulator()
    
    # Verify simulator is accessible
    try:
        stdout, rc = simulator.execute_slurm_command("sinfo")
        if rc != 0:
            pytest.skip("Slurm simulator is not running")
    except Exception as e:
        pytest.skip(f"Failed to connect to Slurm simulator: {e}")
    
    return simulator

@pytest.fixture
def slurm_test_script(tmp_path):
    """Create a simple Slurm test script that produces verifiable output."""
    script_path = tmp_path / "test_job.sh"
    script_content = """#!/bin/bash
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=5:00
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

# Echo job info
echo "Job started at $(date)"
echo "Running on node: $(hostname)"
echo "Slurm job ID: $SLURM_JOB_ID"

# Do some work that produces both stdout and stderr
echo "This goes to stdout"
echo "This goes to stderr" >&2

# Test file creation
WORKDIR="${SLURM_SUBMIT_DIR:-/slurm/jobs}"
echo "Test output" > $WORKDIR/test_output.txt

# Sleep to simulate work
sleep 5

# Final status
echo "Job completed at $(date)"
exit 0
"""
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    return script_path

@pytest.fixture
def failing_test_script(tmp_path):
    """Create a Slurm script that fails for testing error handling."""
    script_path = tmp_path / "failing_job.sh"
    script_content = """#!/bin/bash
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=1:00
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

# Start job
echo "Job started with PID: $$"
echo "About to fail..." >&2

# Sleep briefly to ensure we can catch it in RUNNING state
sleep 2

# Exit with error
echo "Job failed with exit code 1"
exit 1
"""
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    return script_path 