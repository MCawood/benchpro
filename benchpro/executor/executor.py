"""
Executor Classes for BenchPRO.

This module defines the Executor base class and its subclasses (LocalExecutor and SchedulerExecutor)
for handling different execution environments in BenchPRO.
"""

import os
import logging
import subprocess
import shlex
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List

from benchpro.executor.scheduler import get_scheduler


class Executor(ABC):
    """Base class for all BenchPRO executors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Executor.
        
        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def submit_job(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Submit a job for execution.
        
        Args:
            script_path: Path to the job script.
            
        Returns:
            Tuple containing:
                - Success flag (True if successful, False otherwise)
                - Job ID or process ID (if submitted, None otherwise)
        """
        pass
    
    @abstractmethod
    def check_status(self, job_id: str) -> str:
        """
        Check the status of a submitted job.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Status of the job as a string (e.g., "RUNNING", "COMPLETED", "FAILED").
        """
        pass
    
    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a submitted job.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
        """
        pass
    
    @classmethod
    def get_executor(cls, executor_type: str, config: Optional[Dict[str, Any]] = None) -> 'Executor':
        """
        Factory method to create an executor of the specified type.
        
        Args:
            executor_type: Type of executor to create ("local" or "scheduler").
            config: Optional configuration dictionary.
            
        Returns:
            An instance of the specified executor type.
            
        Raises:
            ValueError: If the executor type is not supported.
        """
        if executor_type.lower() == "local":
            return LocalExecutor(config)
        elif executor_type.lower() == "scheduler":
            return SchedulerExecutor(config)
        else:
            raise ValueError(f"Unsupported executor type: {executor_type}")


class LocalExecutor(Executor):
    """Executor for running jobs locally without a scheduler."""
    
    def submit_job(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Run a job script locally using bash.
        
        Args:
            script_path: Path to the job script.
            
        Returns:
            Tuple containing:
                - Success flag (True if successful, False otherwise)
                - Process ID as a string (if started, None otherwise)
        """
        try:
            # Make sure the script is executable
            os.chmod(script_path, 0o755)
            
            # Create a log file path
            log_dir = os.path.dirname(script_path)
            script_name = os.path.basename(script_path)
            log_path = os.path.join(log_dir, f"{os.path.splitext(script_name)[0]}.log")
            
            # Start the process
            with open(log_path, 'w') as log_file:
                process = subprocess.Popen(
                    ['/bin/bash', script_path],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    start_new_session=True  # Detach the process
                )
            
            # Return the process ID as the "job ID"
            pid = str(process.pid)
            self.logger.info(f"Local job started with PID: {pid}")
            self.logger.info(f"Output is being logged to: {log_path}")
            
            return True, pid
            
        except Exception as e:
            self.logger.error(f"Local job submission failed: {str(e)}")
            return False, None
    
    def check_status(self, job_id: str) -> str:
        """
        Check the status of a local job using the process ID.
        
        Args:
            job_id: Process ID of the job to check.
            
        Returns:
            Status of the job as a string ("RUNNING", "COMPLETED", or "FAILED").
        """
        try:
            # Try to get process info using ps
            cmd = f"ps -p {job_id} -o state="
            result = subprocess.run(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # If the process exists, it's running
            if result.returncode == 0 and result.stdout.strip():
                return "RUNNING"
            
            # If we can't find the process, check if it exited successfully
            # This is a simplification - in reality, we'd need to store exit codes
            return "COMPLETED"
            
        except Exception as e:
            self.logger.error(f"Status check failed: {str(e)}")
            return "UNKNOWN"
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a local job by killing the process.
        
        Args:
            job_id: Process ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
        """
        try:
            # Kill the process
            cmd = f"kill {job_id}"
            result = subprocess.run(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                self.logger.info(f"Local job {job_id} cancelled")
                return True
            else:
                self.logger.error(f"Failed to cancel job {job_id}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Job cancellation failed: {str(e)}")
            return False


class SchedulerExecutor(Executor):
    """Executor for running jobs through a job scheduler (e.g., Slurm, PBS)."""
    
    def submit_job(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Submit a job to the scheduler.
        
        Args:
            script_path: Path to the job script.
            
        Returns:
            Tuple containing:
                - Success flag (True if successful, False otherwise)
                - Job ID (if submitted, None otherwise)
        """
        try:
            # Get scheduler type from config
            scheduler_type = self.config.get("type", "slurm")
            
            # Create scheduler instance
            scheduler = get_scheduler(scheduler_type, self.config)
            
            # Submit the job
            job_id = scheduler.submit_job(script_path)
            self.logger.info(f"Job submitted with ID: {job_id}")
            
            return True, job_id
            
        except Exception as e:
            self.logger.error(f"Job submission failed: {str(e)}")
            return False, None
    
    def check_status(self, job_id: str) -> str:
        """
        Check the status of a job using the scheduler.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Status of the job as a string (e.g., "RUNNING", "COMPLETED", "FAILED").
        """
        try:
            # Get scheduler type from config
            scheduler_type = self.config.get("type", "slurm")
            
            # Create scheduler instance
            scheduler = get_scheduler(scheduler_type, self.config)
            
            # Check job status
            return scheduler.check_status(job_id)
            
        except Exception as e:
            self.logger.error(f"Status check failed: {str(e)}")
            return "UNKNOWN"
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job using the scheduler.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
        """
        try:
            # Get scheduler type from config
            scheduler_type = self.config.get("type", "slurm")
            
            # Create scheduler instance
            scheduler = get_scheduler(scheduler_type, self.config)
            
            # Cancel the job
            return scheduler.cancel_job(job_id)
            
        except Exception as e:
            self.logger.error(f"Job cancellation failed: {str(e)}")
            return False 