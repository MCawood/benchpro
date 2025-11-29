import abc
import subprocess
from typing import Dict, List, Optional

from benchpro.core.domain import Job, Task

class SchedulerBackend(abc.ABC):
    @abc.abstractmethod
    def submit_job(self, job: Job) -> str:
        """Submit a job and return the scheduler ID."""
        pass

    @abc.abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        pass

class SlurmBackend(SchedulerBackend):
    def submit_job(self, job: Job) -> str:
        """Submit a job via sbatch."""
        # Write script to temp file or pipe
        # For now, we'll assume the script content is in job.script_content
        
        # In a real implementation, we'd handle file writing properly
        # Here we just pipe to sbatch
        try:
            process = subprocess.Popen(
                ["sbatch"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=job.script_content)
            
            if process.returncode != 0:
                raise RuntimeError(f"sbatch failed: {stderr}")
                
            # Parse job ID (Submitted batch job 123456)
            job_id = stdout.strip().split()[-1]
            return job_id
            
        except FileNotFoundError:
            # Mock for local testing if sbatch isn't found
            print("[Mock] sbatch submitted")
            return "mock_job_123"

    def cancel_job(self, job_id: str) -> bool:
        try:
            subprocess.run(["scancel", job_id], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

class LocalBackend(SchedulerBackend):
    def submit_job(self, job: Job) -> str:
        # Local execution is handled differently (direct process spawning)
        # This might be used if we wrap local execution in a "job" abstraction
        return "local_job"

    def cancel_job(self, job_id: str) -> bool:
        return True
