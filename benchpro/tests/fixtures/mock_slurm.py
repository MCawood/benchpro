"""
Mock SLURM system for testing BenchPRO SLURM functionality.

This module provides a comprehensive mock of SLURM commands and behavior,
allowing tests to validate SLURM integration without requiring actual SLURM installation.
"""

import os
import re
import time
import tempfile
import threading
from typing import Dict, List, Optional, Tuple, Any, Union
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy
import uuid


class JobState(Enum):
    """SLURM job states."""
    PENDING = "PENDING"
    CONFIGURING = "CONFIGURING"
    RUNNING = "RUNNING"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    OUT_OF_MEMORY = "OUT_OF_MEMORY"
    PREEMPTED = "PREEMPTED"


@dataclass
class MockJob:
    """Represents a mock SLURM job."""
    job_id: str
    script_path: str
    state: JobState = JobState.PENDING
    submit_time: float = field(default_factory=time.time)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    exit_code: int = 0
    working_dir: str = field(default_factory=os.getcwd)
    job_name: Optional[str] = None
    nodes: int = 1
    tasks_per_node: int = 1
    time_limit: str = "01:00:00"
    partition: Optional[str] = None
    account: Optional[str] = None
    stdout_file: Optional[str] = None
    stderr_file: Optional[str] = None
    sbatch_options: Dict[str, Any] = field(default_factory=dict)


class MockSlurmSystem:
    """
    Mock SLURM system that simulates realistic SLURM behavior.
    
    This class provides a comprehensive simulation of SLURM commands and job lifecycle,
    enabling thorough testing of SLURM integration without requiring actual SLURM.
    """
    
    def __init__(self, auto_progress_jobs: bool = True, job_run_time: float = 0.1):
        """
        Initialize the mock SLURM system.
        
        Args:
            auto_progress_jobs: Whether jobs should automatically progress through states
            job_run_time: How long jobs should take to run (in seconds)
        """
        self.jobs: Dict[str, MockJob] = {}
        self.job_counter = 1000
        self.auto_progress_jobs = auto_progress_jobs
        self.job_run_time = job_run_time
        self._job_progression_thread = None
        self._stop_progression = False
        
        # Track command calls for verification
        self.command_history: List[Tuple[str, List[str]]] = []
        
        # Configure failure scenarios for testing
        self.fail_submissions = False
        self.fail_status_checks = False
        self.fail_cancellations = False
        self.submission_error_message = "Mock submission error"
        self.status_error_message = "Mock status error"
        self.cancellation_error_message = "Mock cancellation error"
        
        # Start job progression if enabled
        if auto_progress_jobs:
            self._start_job_progression()
    
    def _start_job_progression(self):
        """Start background thread for job state progression."""
        if self._job_progression_thread is None or not self._job_progression_thread.is_alive():
            self._stop_progression = False
            self._job_progression_thread = threading.Thread(target=self._progress_jobs, daemon=True)
            self._job_progression_thread.start()
    
    def _progress_jobs(self):
        """Background thread function to progress job states."""
        while not self._stop_progression:
            current_time = time.time()
            
            for job in list(self.jobs.values()):
                if job.state == JobState.PENDING:
                    # Start job after a brief delay
                    if current_time - job.submit_time > 0.05:
                        job.state = JobState.RUNNING
                        job.start_time = current_time
                
                elif job.state == JobState.RUNNING:
                    # Complete job after run time
                    if job.start_time and current_time - job.start_time > self.job_run_time:
                        job.state = JobState.COMPLETED
                        job.end_time = current_time
            
            time.sleep(0.01)  # Small delay to prevent busy waiting
    
    def stop(self):
        """Stop the mock SLURM system."""
        self._stop_progression = True
        if self._job_progression_thread and self._job_progression_thread.is_alive():
            self._job_progression_thread.join(timeout=1)
    
    def reset(self):
        """Reset the mock system to initial state."""
        self.stop()
        self.jobs.clear()
        self.job_counter = 1000
        self.command_history.clear()
        self.fail_submissions = False
        self.fail_status_checks = False
        self.fail_cancellations = False
        if self.auto_progress_jobs:
            self._start_job_progression()
    
    def _generate_job_id(self) -> str:
        """Generate a unique job ID."""
        job_id = str(self.job_counter)
        self.job_counter += 1
        return job_id
    
    def _parse_sbatch_script(self, script_path: str) -> Dict[str, Any]:
        """Parse SBATCH directives from a script file."""
        directives = {}
        
        if not os.path.exists(script_path):
            return directives
        
        with open(script_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#SBATCH'):
                    # Parse SBATCH directive
                    directive_part = line.replace('#SBATCH', '').strip()
                    
                    # Handle various formats: -J value, --job-name=value, etc.
                    if '=' in directive_part:
                        # Format: --option=value or -o=value
                        key, value = directive_part.split('=', 1)
                        key = key.strip('-').strip()
                        directives[key] = value.strip()
                    else:
                        # Format: -J value or --job-name value
                        parts = directive_part.split(None, 1)
                        if len(parts) == 2:
                            key = parts[0].strip('-').strip()
                            value = parts[1].strip()
                            directives[key] = value
                        elif len(parts) == 1:
                            # Handle flags without values
                            key = parts[0].strip('-').strip()
                            directives[key] = True
        
        return directives
    
    def submit_job(self, script_path: str, extra_args: Optional[List[str]] = None) -> str:
        """
        Mock sbatch command - submit a job.
        
        Args:
            script_path: Path to the job script
            extra_args: Additional sbatch arguments
            
        Returns:
            Job ID string
            
        Raises:
            Exception: If submission fails (when configured to fail)
        """
        self.command_history.append(("sbatch", [script_path] + (extra_args or [])))
        
        if self.fail_submissions:
            raise Exception(self.submission_error_message)
        
        if not os.path.exists(script_path):
            raise Exception(f"sbatch: error: Batch script not found: {script_path}")
        
        # Generate job ID
        job_id = self._generate_job_id()
        
        # Parse script directives
        directives = self._parse_sbatch_script(script_path)
        
        # Create job
        job = MockJob(
            job_id=job_id,
            script_path=script_path,
            job_name=directives.get('J', directives.get('job-name', f'job_{job_id}')),
            nodes=int(directives.get('N', directives.get('nodes', 1))),
            tasks_per_node=int(directives.get('ntasks-per-node', 1)),
            time_limit=directives.get('t', directives.get('time', '01:00:00')),
            partition=directives.get('p', directives.get('partition')),
            account=directives.get('A', directives.get('account')),
            stdout_file=directives.get('o', directives.get('output')),
            stderr_file=directives.get('e', directives.get('error'))
        )
        
        # Store job
        self.jobs[job_id] = job
        
        return f"Submitted batch job {job_id}"
    
    def check_status(self, job_id: str, use_sacct: bool = False) -> str:
        """
        Mock squeue/sacct command - check job status.
        
        Args:
            job_id: Job ID to check
            use_sacct: Whether to use sacct (for completed jobs) vs squeue
            
        Returns:
            Job status string
            
        Raises:
            Exception: If status check fails (when configured to fail)
        """
        command = "sacct" if use_sacct else "squeue"
        self.command_history.append((command, [job_id]))
        
        if self.fail_status_checks:
            raise Exception(self.status_error_message)
        
        if job_id not in self.jobs:
            if use_sacct:
                return ""  # Job not found in accounting
            else:
                raise Exception(f"squeue: error: Invalid job id {job_id}")
        
        job = self.jobs[job_id]
        
        # For squeue, only return running/pending jobs
        if not use_sacct and job.state in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]:
            return ""  # Job not in queue anymore
        
        return job.state.value
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Mock scancel command - cancel a job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if successful
            
        Raises:
            Exception: If cancellation fails (when configured to fail)
        """
        self.command_history.append(("scancel", [job_id]))
        
        if self.fail_cancellations:
            raise Exception(self.cancellation_error_message)
        
        if job_id not in self.jobs:
            raise Exception(f"scancel: error: Invalid job id {job_id}")
        
        job = self.jobs[job_id]
        if job.state in [JobState.PENDING, JobState.RUNNING]:
            job.state = JobState.CANCELLED
            job.end_time = time.time()
        
        return True
    
    def set_job_state(self, job_id: str, state: JobState):
        """
        Manually set a job's state (for testing specific scenarios).
        
        Args:
            job_id: Job ID
            state: New state to set
        """
        if job_id in self.jobs:
            self.jobs[job_id].state = state
            if state in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]:
                self.jobs[job_id].end_time = time.time()
    
    def get_job(self, job_id: str) -> Optional[MockJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[MockJob]:
        """Get all jobs."""
        return list(self.jobs.values())
    
    def wait_for_job_state(self, job_id: str, state: JobState, timeout: float = 5.0) -> bool:
        """
        Wait for a job to reach a specific state.
        
        Args:
            job_id: Job ID to wait for
            state: State to wait for
            timeout: Maximum time to wait
            
        Returns:
            True if job reached the state, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            if job and job.state == state:
                return True
            time.sleep(0.01)
        return False


class MockSlurmCommands:
    """
    Mock implementation of SLURM commands that can be used with subprocess patching.
    
    This class provides method that can be used to replace subprocess.run calls
    with realistic SLURM command behavior.
    """
    
    def __init__(self, slurm_system: MockSlurmSystem):
        """
        Initialize with a reference to the mock SLURM system.
        
        Args:
            slurm_system: The MockSlurmSystem instance to use
        """
        self.slurm_system = slurm_system
    
    def run_command(self, cmd, *args, **kwargs):
        """
        Mock subprocess.run that handles SLURM commands.
        
        Args:
            cmd: Command list (e.g., ['sbatch', 'script.sh'])
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            Mock subprocess result object
        """
        if not isinstance(cmd, list) or len(cmd) == 0:
            raise ValueError("Command must be a non-empty list")
        
        command = cmd[0]
        
        # Create mock result object
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        
        try:
            if command == "sbatch":
                if len(cmd) < 2:
                    result.returncode = 1
                    result.stderr = "sbatch: error: No script specified"
                else:
                    script_path = cmd[-1]  # Last argument is script path
                    extra_args = cmd[1:-1]  # Middle arguments are options
                    output = self.slurm_system.submit_job(script_path, extra_args)
                    result.stdout = output
            
            elif command == "squeue":
                if "-j" in cmd:
                    job_idx = cmd.index("-j") + 1
                    if job_idx < len(cmd):
                        job_id = cmd[job_idx]
                        try:
                            status = self.slurm_system.check_status(job_id, use_sacct=False)
                            result.stdout = status
                        except Exception as e:
                            result.returncode = 1
                            result.stderr = str(e)
                    else:
                        result.returncode = 1
                        result.stderr = "squeue: error: Missing job ID"
                else:
                    result.returncode = 1
                    result.stderr = "squeue: error: Invalid arguments"
            
            elif command == "sacct":
                if "-j" in cmd:
                    job_idx = cmd.index("-j") + 1
                    if job_idx < len(cmd):
                        job_id = cmd[job_idx]
                        try:
                            status = self.slurm_system.check_status(job_id, use_sacct=True)
                            result.stdout = status
                        except Exception as e:
                            result.returncode = 1
                            result.stderr = str(e)
                    else:
                        result.returncode = 1
                        result.stderr = "sacct: error: Missing job ID"
                else:
                    result.returncode = 1
                    result.stderr = "sacct: error: Invalid arguments"
            
            elif command == "scancel":
                if len(cmd) >= 2:
                    job_id = cmd[1]
                    self.slurm_system.cancel_job(job_id)
                    result.stdout = f"Cancelled job {job_id}"
                else:
                    result.returncode = 1
                    result.stderr = "scancel: error: Missing job ID"
            
            else:
                # Unknown command - pass through to actual subprocess
                import subprocess
                return subprocess.run(cmd, *args, **kwargs)
        
        except Exception as e:
            result.returncode = 1
            result.stderr = str(e)
        
        # Simulate subprocess.run behavior with check=True
        if result.returncode != 0 and kwargs.get('check', False):
            import subprocess
            raise subprocess.CalledProcessError(
                result.returncode, 
                cmd, 
                output=result.stdout, 
                stderr=result.stderr
            )
        
        return result


# Global mock system instance for easy access
_global_mock_slurm = None


def get_mock_slurm_system() -> MockSlurmSystem:
    """Get the global mock SLURM system instance."""
    global _global_mock_slurm
    if _global_mock_slurm is None:
        _global_mock_slurm = MockSlurmSystem()
    return _global_mock_slurm


def reset_mock_slurm_system():
    """Reset the global mock SLURM system."""
    global _global_mock_slurm
    if _global_mock_slurm:
        _global_mock_slurm.reset()


def create_mock_slurm_system(auto_progress_jobs: bool = True, job_run_time: float = 0.1) -> MockSlurmSystem:
    """
    Create a new mock SLURM system instance.
    
    Args:
        auto_progress_jobs: Whether jobs should automatically progress through states
        job_run_time: How long jobs should take to run (in seconds)
        
    Returns:
        New MockSlurmSystem instance
    """
    return MockSlurmSystem(auto_progress_jobs=auto_progress_jobs, job_run_time=job_run_time)


def patch_slurm_commands(mock_system: Optional[MockSlurmSystem] = None):
    """
    Context manager that patches subprocess.run to use mock SLURM commands.
    
    Args:
        mock_system: MockSlurmSystem to use, or None to use global instance
        
    Returns:
        Context manager for patching
    """
    if mock_system is None:
        mock_system = get_mock_slurm_system()
    
    mock_commands = MockSlurmCommands(mock_system)
    return patch('subprocess.run', side_effect=mock_commands.run_command) 