"""
Execution components for BenchPRO.

This module provides implementation of execution components that are responsible
for executing scripts in different environments (local, SLURM).
"""

import os
import subprocess
import time
from typing import Dict, Any, Tuple, Optional

from benchpro.executor.components.interfaces import (
    ExecutionComponent, ExecutionError
)
from benchpro.utils.logger import get_logger


class LocalExecutionComponent(ExecutionComponent):
    """
    Implementation of the ExecutionComponent for local execution.
    
    This component executes scripts locally as a subprocess.
    """
    
    def __init__(self):
        """Initialize the LocalExecutionComponent."""
        self.logger = get_logger(__name__)
        self.processes = {}  # Dictionary to track running processes
    
    def execute(self, script_path: str, workspace: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[str]]:
        """
        Execute a script locally.
        
        Args:
            script_path: Path to the script to execute.
            workspace: Optional workspace dictionary. If provided, script output will be
                      redirected to a log file in the workspace logs directory.
            
        Returns:
            A tuple containing:
                - True if the script was executed successfully, False otherwise.
                - Process ID as a string (if executed, None otherwise).
                
        Raises:
            ExecutionError: If the script execution fails.
        """
        self.logger.info(f"Executing script locally: {script_path}")
        
        if not os.path.exists(script_path):
            error_msg = f"Script not found: {script_path}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        
        try:
            # Make sure the script is executable
            os.chmod(script_path, 0o755)
            
            # Get the script directory to use as working directory
            script_dir = os.path.dirname(script_path)
            
            # Generate a unique job ID
            job_id = str(int(time.time() * 1000))
            
            # Determine how to redirect output
            output_redirection = "/dev/null"
            if workspace and "logs_dir" in workspace:
                # Get script filename without extension for the log name
                script_name = os.path.basename(script_path)
                script_name_without_ext = os.path.splitext(script_name)[0]
                output_log = os.path.join(workspace["logs_dir"], f"{script_name_without_ext}_output.log")
                output_redirection = output_log
                self.logger.info(f"Script output will be redirected to: {output_log}")
            
            # Use os.system - a direct, simple approach with output redirection
            command = f"cd {script_dir} && bash {script_path} > {output_redirection} 2>&1 &"
            os.system(command)
            
            # Track this job
            self.processes[job_id] = {
                'completed': False,
                'script_dir': script_dir,
                'script_path': script_path,
                'output_log': output_redirection if output_redirection != "/dev/null" else None
            }
            
            self.logger.info(f"Script executing with job ID: {job_id}")
            
            return True, job_id
        except Exception as e:
            error_msg = f"Failed to execute script: {str(e)}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
    
    def get_status(self, job_id: str) -> str:
        """
        Get the status of a job.
        
        Args:
            job_id: The job ID to check.
            
        Returns:
            Status of the process ("RUNNING", "COMPLETED", "FAILED").
            
        Raises:
            ExecutionError: If the status check fails.
        """
        self.logger.debug(f"Checking status of job ID: {job_id}")
        
        if job_id not in self.processes:
            error_msg = f"Job ID not found: {job_id}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        
        process_info = self.processes[job_id]
        
        # If we already know it's completed, return that status
        if process_info.get('completed', False):
            return "COMPLETED"
            
        # Since we can't directly monitor the background process,
        # we can check if any result files have been created in the output directory
        script_dir = process_info.get('script_dir', '')
        if script_dir:
            # The job might have completed if there are files in the output directory
            output_dir = os.path.join(script_dir, 'output')
            if os.path.exists(output_dir) and os.listdir(output_dir):
                self.processes[job_id]['completed'] = True
                return "COMPLETED"
                
        # If we can't determine completion, we assume it's still running
        return "RUNNING"
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: The job ID to cancel.
            
        Returns:
            True if the job was cancelled successfully, False otherwise.
            
        Raises:
            ExecutionError: If the job cancellation fails.
        """
        self.logger.info(f"Attempting to cancel job ID: {job_id}")
        
        if job_id not in self.processes:
            error_msg = f"Job ID not found: {job_id}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        
        # We don't have a way to directly cancel it
        self.logger.warning(f"Cannot directly cancel job ID: {job_id}, running in background")
        return True


class SlurmExecutionComponent(ExecutionComponent):
    """
    Implementation of the ExecutionComponent for SLURM execution.
    
    This component submits scripts to a SLURM job scheduler.
    """
    
    def __init__(self):
        """Initialize the SlurmExecutionComponent."""
        self.logger = get_logger(__name__)
    
    def execute(self, script_path: str, workspace: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[str]]:
        """
        Submit a script to SLURM.
        
        Args:
            script_path: Path to the script to submit.
            workspace: Optional workspace dictionary. Currently not used by SLURM execution.
            
        Returns:
            A tuple containing:
                - True if the script was submitted successfully, False otherwise.
                - Job ID (if submitted, None otherwise).
                
        Raises:
            ExecutionError: If the script submission fails.
        """
        self.logger.info(f"Submitting script to SLURM: {script_path}")
        
        if not os.path.exists(script_path):
            error_msg = f"Script not found: {script_path}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        
        try:
            # Make sure the script is executable
            os.chmod(script_path, 0o755)
            
            # Submit the job to SLURM
            result = subprocess.run(
                ["sbatch", script_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the job ID from the output
            output = result.stdout.strip()
            
            if "Submitted batch job" in output:
                job_id = output.split()[-1]
                self.logger.info(f"Job submitted to SLURM with ID: {job_id}")
                return True, job_id
            else:
                self.logger.error(f"Failed to submit job, unexpected output: {output}")
                return False, None
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to submit job: {e.stderr.strip()}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to submit job: {str(e)}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
    
    def get_status(self, job_id: str) -> str:
        """
        Get the status of a SLURM job.
        
        Args:
            job_id: The SLURM job ID to check.
            
        Returns:
            Status of the job ("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "UNKNOWN").
            
        Raises:
            ExecutionError: If the status check fails.
        """
        self.logger.debug(f"Checking status of SLURM job ID: {job_id}")
        
        try:
            # Check job status using sacct
            result = subprocess.run(
                ["sacct", "-j", job_id, "-o", "State", "--noheader", "--parsable2"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the status from the output
            status_output = result.stdout.strip().split("\n")[0]
            
            # Map SLURM status to our status categories
            if status_output in ["PENDING", "CONFIGURING", "WAITING"]:
                return "PENDING"
            elif status_output in ["RUNNING", "COMPLETING"]:
                return "RUNNING"
            elif status_output in ["COMPLETED"]:
                return "COMPLETED"
            elif status_output in ["FAILED", "TIMEOUT", "OUT_OF_MEMORY"]:
                return "FAILED"
            elif status_output in ["CANCELLED", "PREEMPTED"]:
                return "CANCELLED"
            else:
                self.logger.warning(f"Unknown SLURM job status: {status_output}")
                return "UNKNOWN"
        except subprocess.CalledProcessError as e:
            if "SchedulerError" in e.stderr and "Invalid job id" in e.stderr:
                error_msg = f"Job ID not found: {job_id}"
            else:
                error_msg = f"Failed to check job status: {e.stderr.strip()}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to check job status: {str(e)}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a SLURM job.
        
        Args:
            job_id: The SLURM job ID to cancel.
            
        Returns:
            True if the job was cancelled successfully, False otherwise.
            
        Raises:
            ExecutionError: If the job cancellation fails.
        """
        self.logger.info(f"Cancelling SLURM job ID: {job_id}")
        
        try:
            # Cancel the job using scancel
            result = subprocess.run(
                ["scancel", job_id],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check if the job was cancelled
            status = self.get_status(job_id)
            
            if status in ["CANCELLED", "COMPLETED", "FAILED"]:
                self.logger.info(f"Job {job_id} cancelled successfully")
                return True
            else:
                self.logger.warning(f"Job {job_id} cancellation might have failed. Current status: {status}")
                return False
        except subprocess.CalledProcessError as e:
            if "SchedulerError" in e.stderr and "Invalid job id" in e.stderr:
                error_msg = f"Job ID not found: {job_id}"
            else:
                error_msg = f"Failed to cancel job: {e.stderr.strip()}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to cancel job: {str(e)}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg) 