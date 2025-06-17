"""
SLURM testing fixtures and utilities.

This module provides pytest fixtures and utilities for testing SLURM functionality
using the mock SLURM system, integrating with the existing centralized test infrastructure.
"""

import os
import tempfile
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import patch

from benchpro.tests.fixtures.mock_slurm import (
    MockSlurmSystem, 
    JobState, 
    create_mock_slurm_system,
    patch_slurm_commands,
    reset_mock_slurm_system
)


@pytest.fixture
def mock_slurm_system():
    """
    Create a fresh mock SLURM system for testing.
    
    This fixture provides a clean MockSlurmSystem instance for each test,
    with auto-progression enabled for realistic job lifecycle simulation.
    """
    system = create_mock_slurm_system(auto_progress_jobs=True, job_run_time=0.1)
    yield system
    system.stop()


@pytest.fixture
def mock_slurm_system_manual():
    """
    Create a mock SLURM system with manual job progression.
    
    This fixture is useful for tests that need precise control over job state transitions.
    """
    system = create_mock_slurm_system(auto_progress_jobs=False, job_run_time=0.1)
    yield system
    system.stop()


@pytest.fixture
def slurm_command_patcher(mock_slurm_system):
    """
    Patch subprocess.run to use mock SLURM commands.
    
    This fixture automatically patches all subprocess calls to SLURM commands,
    redirecting them to the mock SLURM system.
    """
    with patch_slurm_commands(mock_slurm_system) as patcher:
        yield patcher


@pytest.fixture
def slurm_test_env(standardized_test_env, mock_slurm_system):
    """
    Complete SLURM testing environment with standardized test data and mock SLURM.
    
    This fixture combines the standardized test environment with a mock SLURM system,
    providing everything needed for comprehensive SLURM integration testing.
    """
    # Add mock SLURM system to test environment
    test_env = standardized_test_env.copy()
    test_env["mock_slurm"] = mock_slurm_system
    
    # Create sample SLURM job scripts for testing
    _create_sample_slurm_scripts(test_env)
    
    yield test_env


@pytest.fixture
def slurm_integration_test(slurm_test_env, slurm_command_patcher):
    """
    Complete SLURM integration testing setup.
    
    This fixture provides:
    - Standardized test environment with all test data
    - Mock SLURM system with realistic behavior
    - Automatic subprocess patching for SLURM commands
    - Sample SLURM scripts
    """
    yield slurm_test_env


def _create_sample_slurm_scripts(test_env: Dict[str, Any]):
    """Create sample SLURM job scripts for testing."""
    
    # Basic SLURM script
    basic_script_content = """#!/bin/bash
#SBATCH -J test_job
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH -t 00:10:00
#SBATCH -p compute
#SBATCH -A test_account
#SBATCH -o logs/test_job.%j.out
#SBATCH -e logs/test_job.%j.err

echo "Hello from SLURM job"
sleep 1
echo "Job completed successfully"
"""
    
    # Complex SLURM script with more directives
    complex_script_content = """#!/bin/bash
#SBATCH --job-name=complex_test
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=16
#SBATCH --time=01:00:00
#SBATCH --partition=batch
#SBATCH --account=project123
#SBATCH --output=logs/complex_test.%j.out
#SBATCH --error=logs/complex_test.%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=test@example.com

module load gcc/11.2.0
module load openmpi/4.0.5

echo "Starting complex job with $(nproc) processes"
mpirun -np 32 ./test_application
echo "Job finished"
"""
    
    # Script with invalid directives (for error testing)
    invalid_script_content = """#!/bin/bash
#SBATCH -J invalid_job
#SBATCH --invalid-option=bad_value
#SBATCH -t invalid_time_format

echo "This script has invalid SBATCH directives"
"""
    
    # Write scripts to test environment
    scripts_dir = os.path.join(test_env["temp_dir"], "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    
    script_files = {
        "basic_slurm.sh": basic_script_content,
        "complex_slurm.sh": complex_script_content,
        "invalid_slurm.sh": invalid_script_content,
    }
    
    for filename, content in script_files.items():
        script_path = os.path.join(scripts_dir, filename)
        with open(script_path, "w") as f:
            f.write(content)
        os.chmod(script_path, 0o755)  # Make executable
    
    # Add script paths to test environment
    test_env["slurm_scripts"] = {
        name: os.path.join(scripts_dir, filename)
        for name, filename in {
            "basic": "basic_slurm.sh",
            "complex": "complex_slurm.sh", 
            "invalid": "invalid_slurm.sh"
        }.items()
    }


class SlurmTestHelper:
    """
    Helper class for SLURM testing utilities.
    
    Provides convenience methods for common SLURM testing scenarios.
    """
    
    def __init__(self, mock_system: MockSlurmSystem):
        """
        Initialize with a mock SLURM system.
        
        Args:
            mock_system: MockSlurmSystem instance to use
        """
        self.mock_system = mock_system
    
    def submit_test_job(self, script_content: str = None) -> str:
        """
        Submit a test job with optional custom script content.
        
        Args:
            script_content: Custom script content, or None for default
            
        Returns:
            Job ID of submitted job
        """
        if script_content is None:
            script_content = """#!/bin/bash
#SBATCH -J test_helper_job
#SBATCH -N 1
#SBATCH -t 00:05:00

echo "Test job from SlurmTestHelper"
"""
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Submit job
            output = self.mock_system.submit_job(script_path)
            job_id = output.split()[-1]  # Extract job ID
            return job_id
        finally:
            # Clean up temporary script
            os.unlink(script_path)
    
    def wait_for_completion(self, job_id: str, timeout: float = 5.0) -> bool:
        """
        Wait for a job to complete.
        
        Args:
            job_id: Job ID to wait for
            timeout: Maximum time to wait
            
        Returns:
            True if job completed, False if timeout
        """
        return self.mock_system.wait_for_job_state(job_id, JobState.COMPLETED, timeout)
    
    def simulate_job_failure(self, job_id: str):
        """
        Simulate a job failure.
        
        Args:
            job_id: Job ID to fail
        """
        self.mock_system.set_job_state(job_id, JobState.FAILED)
    
    def simulate_network_failure(self):
        """Simulate network failures for testing error handling."""
        self.mock_system.fail_submissions = True
        self.mock_system.fail_status_checks = True
        self.mock_system.fail_cancellations = True
        self.mock_system.submission_error_message = "Connection timeout"
        self.mock_system.status_error_message = "Network unreachable"
        self.mock_system.cancellation_error_message = "Connection refused"
    
    def restore_normal_operation(self):
        """Restore normal operation after simulating failures."""
        self.mock_system.fail_submissions = False
        self.mock_system.fail_status_checks = False
        self.mock_system.fail_cancellations = False
    
    def get_command_history(self) -> List[tuple]:
        """Get the history of SLURM commands that were executed."""
        return self.mock_system.command_history.copy()
    
    def assert_command_called(self, command: str, times: int = None):
        """
        Assert that a SLURM command was called.
        
        Args:
            command: Command name (e.g., 'sbatch', 'squeue')
            times: Expected number of times called, or None to just check if called
            
        Raises:
            AssertionError: If assertion fails
        """
        history = self.get_command_history()
        command_calls = [call for call in history if call[0] == command]
        
        if times is None:
            assert len(command_calls) > 0, f"Command '{command}' was not called"
        else:
            assert len(command_calls) == times, \
                f"Command '{command}' was called {len(command_calls)} times, expected {times}"
    
    def assert_job_reached_state(self, job_id: str, state: JobState):
        """
        Assert that a job reached a specific state.
        
        Args:
            job_id: Job ID to check
            state: Expected state
            
        Raises:
            AssertionError: If assertion fails
        """
        job = self.mock_system.get_job(job_id)
        assert job is not None, f"Job {job_id} not found"
        assert job.state == state, f"Job {job_id} is in state {job.state}, expected {state}"


@pytest.fixture
def slurm_helper(mock_slurm_system):
    """
    Provide a SlurmTestHelper instance for convenient testing.
    
    This fixture creates a helper object that provides convenient methods
    for common SLURM testing scenarios.
    """
    return SlurmTestHelper(mock_slurm_system)


# Convenience functions for use in tests
def create_slurm_script(script_content: str, temp_dir: str) -> str:
    """
    Create a temporary SLURM script file.
    
    Args:
        script_content: Content of the script
        temp_dir: Directory to create script in
        
    Returns:
        Path to created script file
    """
    script_path = os.path.join(temp_dir, f"test_script_{os.getpid()}.sh")
    with open(script_path, "w") as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)
    return script_path


def create_minimal_slurm_script(job_name: str = "test_job", temp_dir: str = None) -> str:
    """
    Create a minimal SLURM script for testing.
    
    Args:
        job_name: Name for the job
        temp_dir: Directory to create script in, or None for system temp
        
    Returns:
        Path to created script file
    """
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()
    
    script_content = f"""#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -N 1
#SBATCH -t 00:05:00

echo "Running {job_name}"
"""
    
    return create_slurm_script(script_content, temp_dir)


def assert_slurm_directives_present(script_content: str, expected_directives: Dict[str, str]):
    """
    Assert that SLURM directives are present in script content.
    
    Args:
        script_content: Content of the script to check
        expected_directives: Dictionary of directive names to expected values
        
    Raises:
        AssertionError: If expected directives are not found
    """
    lines = script_content.split('\n')
    sbatch_lines = [line.strip() for line in lines if line.strip().startswith('#SBATCH')]
    
    for directive, expected_value in expected_directives.items():
        # Look for directive in various formats
        patterns = [
            f"#SBATCH -{directive} {expected_value}",
            f"#SBATCH --{directive}={expected_value}",
            f"#SBATCH -{directive}={expected_value}",
            f"#SBATCH --{directive} {expected_value}",
        ]
        
        found = False
        for pattern in patterns:
            if any(pattern in line for line in sbatch_lines):
                found = True
                break
        
        assert found, f"SBATCH directive '{directive}' with value '{expected_value}' not found in script"


# Export commonly used classes and functions
__all__ = [
    'MockSlurmSystem',
    'JobState', 
    'SlurmTestHelper',
    'create_slurm_script',
    'create_minimal_slurm_script',
    'assert_slurm_directives_present'
] 