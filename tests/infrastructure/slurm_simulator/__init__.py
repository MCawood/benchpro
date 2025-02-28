"""Slurm simulator infrastructure for testing BenchPRO's Slurm executor."""

from pathlib import Path
from dataclasses import dataclass
import subprocess
import os
import re

@dataclass
class SlurmSimulator:
    """Manages interaction with the Slurm simulator VM."""
    
    vm_name: str = "slurm"
    shared_dir: Path = Path("/slurm/jobs")
    host_shared_dir: Path = Path(os.path.expanduser("~/dev/slurm_sim/jobs"))

    def execute_slurm_command(self, command: str) -> tuple[str, int]:
        """Execute a Slurm command in the VM.
        
        Args:
            command: The Slurm command to execute
            
        Returns:
            Tuple of (output, return_code)
        """
        # Use bash -c to properly interpret shell commands and operators
        full_cmd = f"limactl shell --workdir=/slurm/jobs slurm bash -c '{command}'"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.returncode

    def get_cluster_info(self) -> dict:
        """Get information about the Slurm cluster configuration.
        
        Returns:
            Dict containing cluster info (partitions, nodes, etc)
        """
        stdout, rc = self.execute_slurm_command("scontrol show partition")
        if rc != 0:
            raise RuntimeError(f"Failed to get cluster info: {stdout}")
        
        # Parse scontrol output and return structured data
        # TODO: Implement parsing
        return {"partitions": ["debug"], "nodes": ["lima-slurm"]}

    def stage_job_script(self, script_path: Path) -> Path:
        """Stage a job script in the shared directory.
        
        Args:
            script_path: Path to the job script on host
            
        Returns:
            Path to the staged script in VM
        """
        # Copy script to shared dir
        vm_script_path = self.shared_dir / script_path.name
        host_script_path = self.host_shared_dir / script_path.name
        
        # Ensure shared dir exists
        self.host_shared_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy script
        with open(script_path, 'r') as src, open(host_script_path, 'w') as dst:
            dst.write(src.read())
            
        return vm_script_path

    def submit_job(self, script_path: Path) -> str:
        """Submit a job to the Slurm cluster.
        
        Args:
            script_path: Path to the job script
            
        Returns:
            Job ID
        """
        vm_path = self.stage_job_script(script_path)
        stdout, rc = self.execute_slurm_command(f"sbatch {vm_path}")
        if rc != 0:
            raise RuntimeError(f"Failed to submit job: {stdout}")
            
        # Parse job ID from sbatch output
        # Expected format: "Submitted batch job 123456"
        try:
            return stdout.strip().split()[-1]
        except IndexError:
            raise RuntimeError(f"Failed to parse job ID from output: {stdout}")

    def get_job_state(self, job_id: str) -> str:
        """Get the state of a Slurm job.
        
        Args:
            job_id: The Slurm job ID
            
        Returns:
            Job state string (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
        """
        stdout, rc = self.execute_slurm_command(f"scontrol show job {job_id}")
        if rc == 0 and stdout.strip():
            # Parse JobState and ExitCode from scontrol output
            state_match = re.search(r'JobState=(\w+)', stdout)
            exit_code_match = re.search(r'ExitCode=(\d+):(\d+)', stdout)
            reason_match = re.search(r'Reason=(\w+)', stdout)
        
            if state_match:
                job_state = state_match.group(1)
                
                # For completed jobs, check exit code
                if job_state == "COMPLETED":
                    if exit_code_match:
                        exit_code = int(exit_code_match.group(1))
                        if exit_code != 0:
                        return "FAILED"
                return "COMPLETED"
                
                # For cancelled jobs
                if job_state == "CANCELLED":
                return "CANCELLED"
                
                # For failed jobs
                if job_state == "FAILED" or (reason_match and reason_match.group(1) == "NonZeroExitCode"):
                    return "FAILED"
                
                return job_state
        
        # If job not found, check if output file exists
        stdout, rc = self.execute_slurm_command(f"test -f slurm-{job_id}.out && echo exists")
        if rc == 0 and stdout.strip():
            return "COMPLETED"  # Job finished but was cleaned from Slurm's memory
        
        return "PENDING"  # Default to PENDING if we can't determine state

    def cancel_job(self, job_id: str) -> None:
        """Cancel a running Slurm job.
        
        Args:
            job_id: The Slurm job ID to cancel
        """
        stdout, rc = self.execute_slurm_command(f"scancel {job_id}")
        if rc != 0:
            raise RuntimeError(f"Failed to cancel job {job_id}: {stdout}")

    def get_job_output(self, job_id: str) -> tuple[str, str]:
        """Get the stdout/stderr for a job.
        
        Args:
            job_id: The Slurm job ID
            
        Returns:
            Tuple of (stdout, stderr) from the job
        """
        # Default Slurm output files are slurm-<jobid>.out
        stdout_file = self.shared_dir / f"slurm-{job_id}.out"
        stderr_file = self.shared_dir / f"slurm-{job_id}.err"
        
        # Check if files exist in VM
        stdout, rc = self.execute_slurm_command(f"cat {stdout_file}")
        job_stdout = stdout if rc == 0 else ""
        
        stdout, rc = self.execute_slurm_command(f"cat {stderr_file}")
        job_stderr = stdout if rc == 0 else ""
        
        return job_stdout, job_stderr 