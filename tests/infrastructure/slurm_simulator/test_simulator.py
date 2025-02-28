"""Tests for Slurm simulator functionality."""

import pytest
from pathlib import Path
import time

def test_simulator_connection(slurm_simulator):
    """Test basic connection to Slurm simulator."""
    stdout, rc = slurm_simulator.execute_slurm_command("sinfo")
    assert rc == 0
    assert "debug" in stdout
    assert "lima-slurm" in stdout

def test_cluster_info(slurm_simulator):
    """Test getting cluster information."""
    info = slurm_simulator.get_cluster_info()
    assert "partitions" in info
    assert "debug" in info["partitions"]
    assert "nodes" in info
    assert "lima-slurm" in info["nodes"]

def test_successful_job_submission(slurm_simulator, slurm_test_script):
    """Test submitting a successful job and verifying its output."""
    # Submit job
    job_id = slurm_simulator.submit_job(slurm_test_script)
    assert job_id.isdigit()
    
    # Wait for job completion (max 30 seconds)
    start_time = time.time()
    final_state = None
    while time.time() - start_time < 30:
        state = slurm_simulator.get_job_state(job_id)
        if state in ["COMPLETED", "FAILED"]:
            final_state = state
            break
        time.sleep(1)
    
    assert final_state == "COMPLETED", f"Job failed with state {final_state}"
    
    # Check job output
    stdout, stderr = slurm_simulator.get_job_output(job_id)
    
    # Verify expected output
    assert "Job started at" in stdout
    assert "Running on node: lima-slurm" in stdout
    assert f"Slurm job ID: {job_id}" in stdout
    assert "This goes to stdout" in stdout
    assert "Job completed at" in stdout
    
    # Verify stderr
    assert "This goes to stderr" in stderr

def test_failing_job(slurm_simulator, failing_test_script):
    """Test handling of a failing job."""
    # Submit job
    job_id = slurm_simulator.submit_job(failing_test_script)
    
    # Wait for job completion
    start_time = time.time()
    final_state = None
    while time.time() - start_time < 30:
        state = slurm_simulator.get_job_state(job_id)
        if state in ["COMPLETED", "FAILED"]:
            final_state = state
            break
        time.sleep(1)
    
    assert final_state == "FAILED"
    
    # Check error output
    stdout, stderr = slurm_simulator.get_job_output(job_id)
    assert "Job started" in stdout
    assert "About to fail..." in stderr

def test_job_cancellation(slurm_simulator, slurm_test_script):
    """Test cancelling a running job."""
    # Submit job
    job_id = slurm_simulator.submit_job(slurm_test_script)
    
    # Wait for job to start
    start_time = time.time()
    while time.time() - start_time < 10:
        state = slurm_simulator.get_job_state(job_id)
        if state == "RUNNING":
            break
        time.sleep(0.5)
    
    # Cancel the job
    slurm_simulator.cancel_job(job_id)
    
    # Verify job was cancelled
    final_state = slurm_simulator.get_job_state(job_id)
    assert final_state in ["CANCELLED", "FAILED"]

def test_script_staging(slurm_simulator, tmp_path):
    """Test staging a job script."""
    # Create test script
    script = tmp_path / "stage_test.sh"
    script.write_text("#!/bin/bash\necho test")
    script.chmod(0o755)
    
    # Stage script
    vm_path = slurm_simulator.stage_job_script(script)
    assert vm_path.parent == slurm_simulator.shared_dir
    
    # Verify script exists in VM
    stdout, rc = slurm_simulator.execute_slurm_command(f"test -f {vm_path} && echo exists")
    assert rc == 0
    assert "exists" in stdout 

def test_job_output_cleanup(slurm_simulator, slurm_test_script):
    """Test that we can still get job state after Slurm cleans up its internal state."""
    # Submit job
    job_id = slurm_simulator.submit_job(slurm_test_script)
    
    # Wait for job completion
    start_time = time.time()
    while time.time() - start_time < 30:
        state = slurm_simulator.get_job_state(job_id)
        if state == "COMPLETED":
            break
        time.sleep(1)
    
    # Verify job completed
    assert slurm_simulator.get_job_state(job_id) == "COMPLETED"
    
    # Simulate Slurm cleaning up job from memory by forcing scontrol to fail
    stdout, rc = slurm_simulator.execute_slurm_command(f"rm -f /var/spool/slurmd/job{job_id}")
    
    # Should still detect COMPLETED since output file exists
    assert slurm_simulator.get_job_state(job_id) == "COMPLETED"
    
    # Verify we can still get output
    stdout, stderr = slurm_simulator.get_job_output(job_id)
    assert "Job started at" in stdout
    assert "Job completed at" in stdout 

def test_non_zero_exit_code(slurm_simulator, tmp_path):
    """Test that jobs with non-zero exit codes are marked as FAILED."""
    # Create test script that exits with code 2
    script_path = tmp_path / "exit2.sh"
    script_content = """#!/bin/bash
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=1:00

echo "About to exit with code 2"
exit 2
"""
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    
    # Submit job
    job_id = slurm_simulator.submit_job(script_path)
    
    # Wait for job completion
    start_time = time.time()
    final_state = None
    while time.time() - start_time < 30:
        state = slurm_simulator.get_job_state(job_id)
        if state in ["COMPLETED", "FAILED"]:
            final_state = state
            break
        time.sleep(1)
    
    # Verify job failed
    assert final_state == "FAILED"
    
    # Check output
    stdout, stderr = slurm_simulator.get_job_output(job_id)
    assert "About to exit with code 2" in stdout 