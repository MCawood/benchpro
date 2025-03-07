"""
Real workflow tests for BenchPRO CLI.

This module contains realistic end-to-end tests that verify actual workflows 
using the existing BenchPRO CLI commands.
"""

import os
import subprocess
import time
import re
import pytest
import sys

# The command to run BenchPRO CLI
BP_CMD = "bp"

def run_command(cmd_args, check_success=True):
    """
    Run a BenchPRO CLI command and return the result.
    
    Args:
        cmd_args: List of command arguments to pass to bp
        check_success: Whether to assert the command succeeded
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    cmd = [BP_CMD] + cmd_args
    print(f"\nRunning command: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    
    stdout, stderr = process.communicate()
    exit_code = process.returncode
    
    print(f"Exit code: {exit_code}")
    if stdout:
        print(f"Standard output:\n{stdout}")
    if stderr:
        print(f"Standard error:\n{stderr}")
    
    if check_success:
        assert exit_code == 0, f"Command failed with exit code {exit_code}"
    
    return exit_code, stdout, stderr

def extract_job_id(output):
    """
    Extract a job ID from command output.
    
    Args:
        output: Command output text
        
    Returns:
        Job ID if found, None otherwise
    """
    # Look for PID or job ID patterns
    job_id_patterns = [
        r"PID: (\d+)",
        r"job[- ]id[: ]+(\d+)",
        r"with PID: (\d+)"
    ]
    
    for pattern in job_id_patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def wait_for_job_completion(job_id, max_wait=60, check_interval=2):
    """
    Wait for a job to complete.
    
    Args:
        job_id: ID of the job to wait for
        max_wait: Maximum seconds to wait
        check_interval: Seconds between checks
        
    Returns:
        True if job completed, False if timed out
    """
    print(f"Waiting for job {job_id} to complete...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check job status
        exit_code, stdout, stderr = run_command(["status", "--job-id", job_id], check_success=False)
        
        # Check if completed or failed
        if "COMPLETED" in stdout or "COMPLETED" in stderr:
            print(f"Job {job_id} completed")
            return True
        
        if any(status in stdout or status in stderr for status in ["FAILED", "ERROR", "CANCELLED"]):
            print(f"Job {job_id} ended with status: {stdout}")
            return True
        
        # Wait before checking again
        time.sleep(check_interval)
    
    print(f"Timed out waiting for job {job_id}")
    return False

def check_required_files():
    """
    Check if the required input files for testing exist.
    
    Returns:
        Tuple of (files_exist: bool, message: str)
    """
    # Check for hello_world source file
    hello_world_source = os.path.expanduser("~/.benchpro/inputs/source/hello_world.c")
    if not os.path.exists(hello_world_source):
        return False, f"Source file not found: {hello_world_source}"
    
    # Check for benchmark profile
    hello_world_benchmark = os.path.expanduser("~/.benchpro/inputs/benchmark/hello_world.yaml")
    if not os.path.exists(hello_world_benchmark):
        return False, f"Benchmark profile not found: {hello_world_benchmark}"
    
    # Check for application profile
    hello_world_app = os.path.expanduser("~/.benchpro/inputs/application/hello_world.yaml")
    if not os.path.exists(hello_world_app):
        return False, f"Application profile not found: {hello_world_app}"
    
    return True, "All required files exist"

def test_build_run_capture_workflow():
    """Test a complete workflow: build -> run -> capture."""
    # Check if required files exist
    files_exist, message = check_required_files()
    if not files_exist:
        pytest.skip(message)
    
    # Build the application
    print("\nRunning command: bp build hello_world")
    exit_code, stdout, stderr = run_command(["build", "hello_world"])
    print(f"Exit code: {exit_code}")
    print(f"Standard output:\n{stdout}")
    print(f"Standard error:\n{stderr}")
    
    assert "Application build script generated" in stdout, "Build should generate a script"
    assert "started with PID" in stdout, "Build should start a process"
    
    # Extract the job ID from stdout
    build_job_id = extract_job_id(stdout)
    assert build_job_id is not None, "Should be able to extract job ID from build output"
    
    print(f"\nWaiting for build job {build_job_id} to complete...")
    wait_for_job_completion(build_job_id)
    
    # Run the benchmark
    print("\nRunning command: bp bench hello_world")
    exit_code, stdout, stderr = run_command(["bench", "hello_world"])
    print(f"Exit code: {exit_code}")
    print(f"Standard output:\n{stdout}")
    print(f"Standard error:\n{stderr}")
    
    assert "Benchmark run script generated" in stdout, "Benchmark should generate a script"
    assert "started with PID" in stdout, "Benchmark should start a process"
    
    # Extract the job ID from stdout
    benchmark_job_id = extract_job_id(stdout)
    assert benchmark_job_id is not None, "Should be able to extract job ID from benchmark output"
    
    print(f"Extracted job ID: {benchmark_job_id}")
    print(f"Waiting for job {benchmark_job_id} to complete...")
    wait_for_job_completion(benchmark_job_id)
    
    # Capture results
    print(f"\nRunning command: bp capture --job-id {benchmark_job_id}")
    exit_code, stdout, stderr = run_command(["capture", "--job-id", benchmark_job_id])
    print(f"Exit code: {exit_code}")
    print(f"Standard output:\n{stdout}")
    print(f"Standard error:\n{stderr}")
    
    assert "Results captured successfully" in stdout, "Results should be captured successfully"
    assert "execution_time" in stdout, "Execution time should be reported"
    
    print("\nComplete workflow test passed successfully!")

if __name__ == "__main__":
    print("Running real workflow tests...")
    
    # Check if required files exist before running tests
    files_exist, message = check_required_files()
    if not files_exist:
        print(f"Skipping tests: {message}")
        print("Please ensure the required files are in place before running these tests.")
    else:
        test_build_run_capture_workflow() 