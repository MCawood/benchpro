"""
Execution Components for BenchPRO Task composition.

This module defines components for executing scripts locally or via a scheduler.
"""

import os
import subprocess
import shlex
from typing import Dict, Any, Optional, Tuple, List

from benchpro.executor.components.interfaces import (
    ExecutionComponent, ExecutionError, StatusCheckError, CancellationError
)
from benchpro.executor.scheduler import get_scheduler, SubmissionError, Scheduler
from benchpro.utils.logger import get_logger


class LocalExecutionComponent(ExecutionComponent):
    """Execution component for running scripts locally."""
    
    def __init__(self):
        """Initialize the local execution component."""
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing LocalExecutionComponent")
    
    def execute(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Execute a script locally using bash.
        
        Args:
            script_path: Path to the script to execute.
            
        Returns:
            A tuple containing:
                - True if the script was successfully submitted, False otherwise.
                - Process ID as a string (if submitted, None otherwise).
                
        Raises:
            ExecutionError: If the script cannot be executed.
        """
        self.logger.info(f"Executing script locally: {script_path}")
        
        try:
            # Make sure the script is executable
            os.chmod(script_path, 0o755)
            self.logger.debug(f"Made script executable: {script_path}")
            
            # Create a log file path
            log_dir = os.path.dirname(script_path)
            script_name = os.path.basename(script_path)
            log_path = os.path.join(log_dir, f"{os.path.splitext(script_name)[0]}.log")
            self.logger.debug(f"Job output will be logged to: {log_path}")
            
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
            self.logger.error(f"Local execution failed: {str(e)}")
            raise ExecutionError(f"Failed to execute script locally: {str(e)}")
    
    def get_status(self, job_id: str) -> str:
        """
        Check the status of a local job using the process ID.
        
        Args:
            job_id: Process ID of the job to check.
            
        Returns:
            Status of the job as a string ("RUNNING", "COMPLETED", or "FAILED").
            
        Raises:
            StatusCheckError: If the status cannot be checked.
        """
        self.logger.debug(f"Checking status of local job with PID: {job_id}")
        
        try:
            # Try to get process info using ps
            cmd = f"ps -p {job_id} -o state="
            self.logger.debug(f"Running command: {cmd}")
            
            result = subprocess.run(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # If the process exists, it's running
            if result.returncode == 0 and result.stdout.strip():
                status = "RUNNING"
                self.logger.debug(f"Job {job_id} is still running")
            else:
                # If we can't find the process, check if it exited successfully
                # This is a simplification - in reality, we'd need to store exit codes
                status = "COMPLETED"
                self.logger.debug(f"Job {job_id} has completed")
                
            return status
            
        except Exception as e:
            self.logger.error(f"Status check failed for job {job_id}: {str(e)}")
            raise StatusCheckError(f"Failed to check status for job {job_id}: {str(e)}")
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a local job by killing the process.
        
        Args:
            job_id: Process ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
            
        Raises:
            CancellationError: If the job cannot be cancelled.
        """
        self.logger.info(f"Cancelling local job with PID: {job_id}")
        
        try:
            # Kill the process
            cmd = f"kill {job_id}"
            self.logger.debug(f"Running command: {cmd}")
            
            result = subprocess.run(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                self.logger.info(f"Local job {job_id} successfully cancelled")
                return True
            else:
                error_msg = f"Failed to cancel job {job_id}: {result.stderr}"
                self.logger.error(error_msg)
                raise CancellationError(error_msg)
                
        except Exception as e:
            self.logger.error(f"Job cancellation failed for job {job_id}: {str(e)}")
            raise CancellationError(f"Failed to cancel job {job_id}: {str(e)}")


class SlurmExecutionComponent(ExecutionComponent):
    """Execution component for running scripts via Slurm scheduler."""
    
    def __init__(self, scheduler_config: Optional[Dict[str, Any]] = None, scheduler: Optional[Scheduler] = None):
        """
        Initialize the Slurm execution component.
        
        Args:
            scheduler_config: Optional configuration for the Slurm scheduler.
            scheduler: Optional scheduler instance for testing purposes.
        """
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing SlurmExecutionComponent")
        
        self.scheduler_config = scheduler_config or {}
        self.scheduler = scheduler or self._create_scheduler()
    
    def _create_scheduler(self) -> Scheduler:
        """
        Create a Slurm scheduler instance.
        
        Returns:
            Slurm scheduler instance.
        """
        try:
            return get_scheduler("slurm", self.scheduler_config)
        except Exception as e:
            self.logger.error(f"Failed to create Slurm scheduler: {str(e)}")
            raise ExecutionError(f"Failed to create Slurm scheduler: {str(e)}")
    
    def execute(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Submit a script to the Slurm scheduler.
        
        Args:
            script_path: Path to the script to execute.
            
        Returns:
            A tuple containing:
                - True if the script was successfully submitted, False otherwise.
                - Job ID (if submitted, None otherwise).
                
        Raises:
            ExecutionError: If the script cannot be submitted.
        """
        self.logger.info(f"Submitting script to Slurm: {script_path}")
        
        try:
            # Make sure the script is executable
            os.chmod(script_path, 0o755)
            self.logger.debug(f"Made script executable: {script_path}")
            
            # Submit the job
            job_id = self.scheduler.submit_job(script_path)
            self.logger.info(f"Job submitted to Slurm with ID: {job_id}")
            
            return True, job_id
            
        except SubmissionError as e:
            self.logger.error(f"Slurm submission failed: {str(e)}")
            raise ExecutionError(f"Failed to submit job to Slurm: {str(e)}")
        except Exception as e:
            self.logger.error(f"Slurm submission failed: {str(e)}")
            raise ExecutionError(f"Failed to submit job to Slurm: {str(e)}")
    
    def get_status(self, job_id: str) -> str:
        """
        Check the status of a Slurm job.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Status of the job as a string.
            
        Raises:
            StatusCheckError: If the status cannot be checked.
        """
        self.logger.debug(f"Checking status of Slurm job with ID: {job_id}")
        
        try:
            status = self.scheduler.check_status(job_id)
            self.logger.debug(f"Slurm job {job_id} status: {status}")
            return status
            
        except Exception as e:
            self.logger.error(f"Status check failed for job {job_id}: {str(e)}")
            raise StatusCheckError(f"Failed to check status for job {job_id}: {str(e)}")
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a Slurm job.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
            
        Raises:
            CancellationError: If the job cannot be cancelled.
        """
        self.logger.info(f"Cancelling Slurm job with ID: {job_id}")
        
        try:
            result = self.scheduler.cancel_job(job_id)
            
            if result:
                self.logger.info(f"Slurm job {job_id} successfully cancelled")
                return True
            else:
                error_msg = f"Failed to cancel Slurm job {job_id}"
                self.logger.error(error_msg)
                raise CancellationError(error_msg)
                
        except Exception as e:
            self.logger.error(f"Job cancellation failed for job {job_id}: {str(e)}")
            raise CancellationError(f"Failed to cancel job {job_id}: {str(e)}") 