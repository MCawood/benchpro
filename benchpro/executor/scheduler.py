"""
Job Scheduler Abstraction for BenchPRO.

This module provides an abstract interface for job submission with implementations
for different job schedulers (e.g., Slurm, PBS).
"""

import os
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class Scheduler(ABC):
    """
    Abstract base class for job schedulers.
    
    This class defines the interface that all scheduler implementations must follow.
    """
    
    @abstractmethod
    def submit_job(self, script_path: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit a job to the scheduler.
        
        Args:
            script_path: Path to the job script file.
            context: Optional additional context for job submission.
            
        Returns:
            Job ID as a string.
            
        Raises:
            SubmissionError: If the job submission fails.
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
            
        Raises:
            StatusCheckError: If the status check fails.
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
            
        Raises:
            CancellationError: If the job cancellation fails.
        """
        pass


class SubmissionError(Exception):
    """Exception raised when job submission fails."""
    pass


class StatusCheckError(Exception):
    """Exception raised when job status check fails."""
    pass


class CancellationError(Exception):
    """Exception raised when job cancellation fails."""
    pass


class SlurmScheduler(Scheduler):
    """
    Slurm scheduler implementation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Slurm scheduler.
        
        Args:
            config: Optional configuration for the scheduler.
        """
        self.config = config or {}
        
    def submit_job(self, script_path: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit a job to Slurm using sbatch.
        
        Args:
            script_path: Path to the job script file.
            context: Optional additional context for job submission.
            
        Returns:
            Job ID as a string.
            
        Raises:
            SubmissionError: If the job submission fails.
        """
        try:
            # Build the sbatch command
            cmd = ["sbatch"]
            
            # Add any additional sbatch options from context
            if context and "sbatch_options" in context:
                for option, value in context["sbatch_options"].items():
                    cmd.extend([f"--{option}", str(value)])
            
            # Add the script path
            cmd.append(script_path)
            
            # Execute the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Parse the job ID from the output
            # Expected output: "Submitted batch job 12345"
            output = result.stdout.strip()
            if "Submitted batch job" in output:
                job_id = output.split()[-1]
                return job_id
            else:
                raise SubmissionError(f"Failed to parse job ID from output: {output}")
                
        except subprocess.CalledProcessError as e:
            raise SubmissionError(f"Job submission failed: {e.stderr}")
        except Exception as e:
            raise SubmissionError(f"Job submission failed: {str(e)}")
    
    def check_status(self, job_id: str) -> str:
        """
        Check the status of a Slurm job using squeue.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Status of the job as a string (e.g., "RUNNING", "COMPLETED", "FAILED").
            
        Raises:
            StatusCheckError: If the status check fails.
        """
        try:
            # Build the squeue command
            cmd = ["squeue", "-j", job_id, "-h", "-o", "%T"]
            
            # Execute the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # If the job is not found in the queue, check sacct to see if it's completed
            if result.returncode != 0 or not result.stdout.strip():
                # Build the sacct command
                cmd = ["sacct", "-j", job_id, "-n", "-o", "State"]
                
                # Execute the command
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    status = result.stdout.strip().split()[0]
                    if "COMPLETED" in status:
                        return "COMPLETED"
                    elif "FAILED" in status or "CANCELLED" in status or "TIMEOUT" in status:
                        return "FAILED"
                    else:
                        return status
                else:
                    return "UNKNOWN"
            else:
                return result.stdout.strip()
                
        except Exception as e:
            raise StatusCheckError(f"Status check failed: {str(e)}")
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a Slurm job using scancel.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
            
        Raises:
            CancellationError: If the job cancellation fails.
        """
        try:
            # Build the scancel command
            cmd = ["scancel", job_id]
            
            # Execute the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                return True
            else:
                raise CancellationError(f"Job cancellation failed: {result.stderr}")
                
        except Exception as e:
            raise CancellationError(f"Job cancellation failed: {str(e)}")


def get_scheduler(scheduler_type: str, config: Optional[Dict[str, Any]] = None) -> Scheduler:
    """
    Factory function to get a scheduler instance based on the type.
    
    Args:
        scheduler_type: Type of scheduler to create (e.g., "slurm", "pbs").
        config: Optional configuration for the scheduler.
        
    Returns:
        Scheduler instance.
        
    Raises:
        ValueError: If the scheduler type is not supported.
    """
    if scheduler_type.lower() == "slurm":
        return SlurmScheduler(config)
    else:
        raise ValueError(f"Unsupported scheduler type: {scheduler_type}") 