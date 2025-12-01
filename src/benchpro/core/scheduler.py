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

    @abc.abstractmethod
    def query_job_status(self, job_ids: List[str]) -> Dict[str, str]:
        """Query the status of multiple jobs. Returns a dict mapping job_id to status."""
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

    def query_job_status(self, job_ids: List[str]) -> Dict[str, str]:
        """Query job status using sacct."""
        if not job_ids:
            return {}
            
        # Join job IDs for the command
        job_list = ",".join(job_ids)
        
        # We use sacct to get the state
        # Format: JobID,State
        # -n: no header
        # -P: parsable (| separator)
        cmd = ["sacct", "-n", "-P", "--format=JobID,State", "-j", job_list]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            
            status_map = {}
            for line in output.split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 2:
                    jid = parts[0]
                    state = parts[1].split()[0] # Take first word (e.g. CANCELLED by ...)
                    
                    # Handle job steps (123.batch, 123.0) - we only care about the main job
                    if "." in jid:
                        continue
                        
                    # Map Slurm state to BenchPRO state
                    # PENDING, RUNNING, COMPLETED, FAILED, TIMEOUT, CANCELLED, NODE_FAIL
                    status_map[jid] = state
            
            return status_map
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback or error
            return {}

class LocalBackend(SchedulerBackend):
    def submit_job(self, job: Job) -> str:
        # Local execution is handled differently (direct process spawning)
        # This might be used if we wrap local execution in a "job" abstraction
        return "local_job"

    def cancel_job(self, job_id: str) -> bool:
        return True

    def query_job_status(self, job_ids: List[str]) -> Dict[str, str]:
        # Local jobs are instantaneous in this MVP, so we don't really query them async
        # But if we did, we'd check process IDs
        return {}
