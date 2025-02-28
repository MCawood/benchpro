"""Slurm job scheduler executor implementation.

This module provides the SlurmExecutor class which implements job execution via the Slurm
workload manager. It handles job submission, monitoring, cancellation and resource usage
tracking through Slurm's command line tools (sbatch, squeue, scancel, sacct, sstat).

The executor translates BenchPRO job resources into Slurm directives and manages job
lifecycle through Slurm's job states. It provides robust error handling and validation
of resource specifications.

When use_slurm_simulator is enabled in settings, commands are executed against a local
Slurm simulator instead of the system Slurm installation.

Example:
    executor = SlurmExecutor(working_dir=Path("/path/to/work"))
    job = Job(name="test", working_dir=Path("/path/to/job"), ...)
    
    # Submit job
    await executor.submit_job(job)
    
    # Check status
    status = await executor.get_job_status(job)
    
    # Cancel if needed
    await executor.cancel_job(job)

Note:
    This implementation assumes either:
    - Slurm commands are available in the system PATH (when use_slurm_simulator=False)
    - Slurm simulator is properly configured (when use_slurm_simulator=True)
    The executor must have appropriate permissions to submit and manage jobs.
"""

import asyncio
import re
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.ports.executor import ExecutionError, ResourceError
from benchpro.core.executor.scheduler import SchedulerExecutor
from benchpro.core.services.settings import Settings

class SlurmExecutor(SchedulerExecutor):
    """Executor implementation for Slurm job scheduler.
    
    This class implements the abstract SchedulerExecutor interface for the Slurm
    workload manager. It provides methods to:
    - Submit jobs via sbatch
    - Monitor job status via squeue/sacct
    - Cancel jobs via scancel
    - Track resource usage via sstat
    - Validate and translate job resources to Slurm directives
    
    The executor maintains a mapping of BenchPRO job IDs to Slurm job IDs and
    handles all communication with the Slurm commands.
    
    When use_slurm_simulator is enabled in settings, commands are executed against
    a local Slurm simulator instead of the system Slurm installation.
    
    Attributes:
        working_dir: Base directory for job files
        env: Dictionary of environment variables to set in job scripts
        _job_ids: Mapping of BenchPRO job IDs to Slurm job IDs
    """
    
    def __init__(self, working_dir: Path, env: Optional[Dict[str, str]] = None):
        """Initialize Slurm executor.
        
        Args:
            working_dir: Base directory for executor operations
            env: Optional environment variables for task execution
        """
        super().__init__(working_dir, env)
        settings = Settings()
        slurm_config = settings.get("executor", {}).get("slurm_simulator", {})
        self.simulator_mode = slurm_config.get("enabled", False)
        if self.simulator_mode:
            logger.debug("Running in Slurm simulator mode")
        self.env: Dict[str, str] = {}
    
    async def _execute_slurm_command(self, command: str, *args: str) -> Tuple[bytes, bytes, int]:
        """Execute a Slurm command, either directly or via simulator.
        
        Args:
            command: The Slurm command to execute (e.g. sbatch, squeue)
            *args: Additional command arguments
            
        Returns:
            Tuple of (stdout, stderr, return_code)
            
        Raises:
            ExecutionError: If command execution fails
        """
        use_simulator = self._settings.get("use_slurm_simulator", False)
        
        if use_simulator:
            sim_config = self._settings.get("slurm_simulator", {})
            connection_type = sim_config.get("connection_type", "ssh")
            
            if connection_type == "lima":
                # Execute via limactl shell
                instance = sim_config.get("instance", "slurm")
                full_command = ["limactl", "shell", instance, command] + list(args)
                
            elif connection_type == "ssh":
                # Build SSH command
                ssh_cmd = ["ssh"]
                if port := sim_config.get("port"):
                    ssh_cmd.extend(["-p", str(port)])
                if key_file := sim_config.get("key_file"):
                    ssh_cmd.extend(["-i", str(key_file)])
                if username := sim_config.get("username"):
                    host = f"{username}@{sim_config['host']}"
                else:
                    host = sim_config["host"]
                ssh_cmd.append(host)
                full_command = ssh_cmd + [command] + list(args)
                
            elif connection_type == "docker":
                # Execute in Docker container
                full_command = ["docker", "exec", sim_config["host"], command] + list(args)
                
            else:  # local
                # Execute locally with any environment variables
                full_command = [command] + list(args)
                
            # Add environment variables if specified
            env = os.environ.copy()
            if env_vars := sim_config.get("env_vars"):
                env.update(env_vars)
                
        else:
            # Use system Slurm commands directly
            full_command = [command] + list(args)
            env = os.environ.copy()
            
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await proc.communicate()
            return stdout, stderr, proc.returncode
            
        except (OSError, subprocess.SubprocessError) as e:
            raise ExecutionError(f"Failed to execute {command}: {str(e)}")
        
    async def _submit_to_scheduler(self, job: Job, script_path: Path) -> str:
        """Submit job to Slurm scheduler.
        
        Args:
            job: Job to submit
            script_path: Path to job script
            
        Returns:
            Slurm job ID
            
        Raises:
            ExecutionError: If submission fails or job ID cannot be parsed
        """
        if not script_path.exists():
            raise ExecutionError(f"Job script not found at {script_path}")
            
        stdout, stderr, returncode = await self._execute_slurm_command(
            "sbatch", str(script_path)
        )
        
        if returncode != 0:
            error_msg = stderr.decode().strip() or "Unknown error"
            raise ExecutionError(f"sbatch failed: {error_msg} (return code: {returncode})")
            
        # Parse job ID from output (format: "Submitted batch job 123456")
        match = re.search(r"Submitted batch job (\d+)", stdout.decode())
        if not match:
            raise ExecutionError(
                "Could not parse job ID from sbatch output. "
                f"Expected format 'Submitted batch job <ID>', got: {stdout.decode()}"
            )
            
        return match.group(1)
        
    async def _cancel_scheduler_job(self, scheduler_job_id: str) -> None:
        """Cancel a running Slurm job.
        
        Args:
            scheduler_job_id: Slurm job ID to cancel
            
        Raises:
            ExecutionError: If cancellation fails
        """
        stdout, stderr, returncode = await self._execute_slurm_command(
            "scancel", scheduler_job_id
        )
        
        if returncode != 0:
            error_msg = stderr.decode().strip() or "Unknown error"
            raise ExecutionError(
                f"Failed to cancel job {scheduler_job_id}: {error_msg} "
                f"(return code: {returncode})"
            )
        
    async def _get_scheduler_job_status(self, job_id: str) -> str:
        """Get status of job from Slurm.

        Args:
            job_id: Slurm job ID

        Returns:
            Job state as string

        Raises:
            ExecutionError: If status check fails or job not found
        """
        # First check if job is in queue
        stdout, stderr, returncode = await self._execute_slurm_command(
            "squeue",
            "-h",  # No header
            "-o",  # Output format
            "%T",  # Just state
            "-j",  # Job ID
            job_id
        )

        if returncode == 0 and stdout:
            # Job found in queue, parse state
            state = stdout.decode().strip()
            return self._map_slurm_state(state)

        # Job not in queue, check sacct for completed jobs
        stdout, stderr, returncode = await self._execute_slurm_command(
            "sacct",
            "-n",  # No header
            "-P",  # Parsable output
            "-j",  # Job ID
            job_id,
            "-o",  # Output format
            "JobID,State,ExitCode"  # Fields to show
        )

        if returncode != 0:
            error_msg = stderr.decode().strip() or "Unknown error"
            raise ExecutionError(
                f"Failed to get job status: {error_msg} "
                f"(return code: {returncode})"
            )

        if stdout:
            # Parse state from sacct output
            try:
                state = stdout.decode().strip().split("|")[1]
                return self._map_slurm_state(state)
            except IndexError:
                raise ExecutionError(
                    f"Invalid sacct output format. Expected '|' separated values, "
                    f"got: {stdout.decode()}"
                )

        raise ExecutionError(
            f"Job {job_id} not found in queue or accounting records. "
            "The job may have been deleted or may never have existed."
        )
        
    def _translate_resources(self, job: Job) -> Dict[str, str]:
        """Convert job resources to Slurm directives.
        
        Args:
            job: Job containing resource requirements
            
        Returns:
            Dictionary of Slurm directives
        """
        directives = {
            "--nodes": str(job.resources.get("nodes", 1)),
            "--ntasks-per-node": str(job.resources.get("cores", 1)),
            "--mem": job.resources.get("memory", "1G"),
            "--time": job.resources.get("walltime", "1:00:00")
        }
        
        # Add optional directives if specified
        optional_fields = ["partition", "qos", "account"]
        for field in optional_fields:
            if field in job.resources:
                directives[f"--{field}"] = job.resources[field]
                
        return directives
        
    async def validate_resources(self, job: Job) -> bool:
        """Validate job resources for Slurm.
        
        Args:
            job: Job to validate resources for
            
        Returns:
            True if resources are valid
            
        Raises:
            ResourceError: If resources are invalid or in wrong format
        """
        # Validate memory format (e.g. "8G", "1024M")
        memory = job.resources.get("memory")
        if memory and not re.match(r"^\d+[KMGT]$", memory):
            raise ResourceError(
                f"Invalid memory format: {memory}. "
                "Expected format: <number>[K|M|G|T] (e.g. '8G', '1024M')"
            )
            
        # Validate walltime format (HH:MM:SS)
        walltime = job.resources.get("walltime")
        if walltime and not re.match(r"^\d+:\d{2}:\d{2}$", walltime):
            raise ResourceError(
                f"Invalid walltime format: {walltime}. "
                "Expected format: HH:MM:SS (e.g. '1:00:00')"
            )
            
        return True
        
    def _generate_job_script(self, job: Job, script_path: Path) -> None:
        """Generate Slurm job script.
        
        Args:
            job: Job to generate script for
            script_path: Where to write the script
        """
        directives = self._translate_resources(job)
        
        script = "#!/bin/bash\n"
        
        # Add Slurm directives
        for key, value in directives.items():
            script += f"#SBATCH {key}={value}\n"
            
        # Add environment setup
        script += "\n# Environment setup\n"
        script += "set -e\n"  # Exit on error
        
        # Add environment variables
        if self.env:
            script += "\n# Environment variables\n"
            for key, value in self.env.items():
                script += f"export {key}={value}\n"
        
        # Add task commands
        for task in job.tasks:
            script += f"\n# Task: {task.name}\n"
            if task.template_path:
                script += f"bash {task.template_path}\n"
            else:
                script += f"{task.command}\n"
            
        script_path.write_text(script)
        script_path.chmod(0o755)  # Make executable
        
    async def get_resource_usage(self, job: Job) -> Dict[str, float]:
        """Get current resource usage for a running job.
        
        Retrieves memory and CPU usage statistics from Slurm's sstat command.
        Memory values are converted from KB to MB for consistency.
        
        Args:
            job: Job to get resource usage for. Must be in RUNNING state.
            
        Returns:
            Dictionary containing:
                memory_mb: Peak memory usage in MB
                virtual_memory_mb: Peak virtual memory in MB  
                cpu_time: Total CPU time in seconds
                
        Raises:
            ExecutionError: If sstat fails or output cannot be parsed
            KeyError: If job ID mapping not found
        """
        # Get Slurm job ID
        scheduler_job_id = self._job_ids.get(job.id)
        if not scheduler_job_id:
            raise KeyError(f"No Slurm job ID found for job {job.id}")
            
        # Run sstat to get resource usage
        stdout, stderr, returncode = await self._execute_slurm_command(
            "sstat",
            "-n",  # No header 
            "-P",  # Parsable output
            "-j",  # Job ID
            scheduler_job_id,
            "-o",  # Output format
            "MaxRSS,MaxVMSize,TotalCPU"  # Fields to show
        )
        
        if returncode != 0:
            error_msg = stderr.decode().strip() or "Unknown error"
            raise ExecutionError(f"sstat failed: {error_msg}")
            
        # Parse resource usage from sstat output
        try:
            maxrss, maxvmsize, cputime = stdout.decode().strip().split("|")
            
            # Convert memory values from KB to MB
            memory_mb = float(maxrss.replace("K", "")) / 1024 if maxrss else 0.0
            vmem_mb = float(maxvmsize.replace("K", "")) / 1024 if maxvmsize else 0.0
            
            # Parse CPU time (format: [DD-[HH:]]MM:SS)
            cpu_time = 0.0
            if cputime:
                parts = cputime.split("-")
                if len(parts) > 1:
                    # Has days
                    days = int(parts[0])
                    time_parts = parts[1].split(":")
                else:
                    days = 0
                    time_parts = parts[0].split(":")
                    
                if len(time_parts) == 3:
                    # HH:MM:SS
                    hours, minutes, seconds = map(int, time_parts)
                else:
                    # MM:SS
                    minutes, seconds = map(int, time_parts)
                    hours = 0
                    
                cpu_time = (days * 24 * 3600) + (hours * 3600) + (minutes * 60) + seconds
                
            return {
                "memory_mb": memory_mb,
                "virtual_memory_mb": vmem_mb,
                "cpu_time": cpu_time
            }
            
        except (ValueError, IndexError) as e:
            raise ExecutionError(f"Failed to parse sstat output: {str(e)}")
            
    def _map_slurm_state(self, state: str) -> str:
        """Map Slurm job state to BenchPRO job state.
        
        This method translates Slurm-specific job states into the standard
        BenchPRO job states. The mapping handles all common Slurm states
        including edge cases like timeouts.
        
        Args:
            state: Raw Slurm job state string
            
        Returns:
            Corresponding BenchPRO job state value
            
        Note:
            Unknown states are passed through unchanged for debugging
        """
        state_map = {
            "PENDING": JobState.QUEUED.value,
            "RUNNING": JobState.RUNNING.value,
            "COMPLETED": JobState.COMPLETED.value,
            "FAILED": JobState.FAILED.value,
            "CANCELLED": JobState.CANCELLED.value,
            "TIMEOUT": JobState.FAILED.value
        }
        return state_map.get(state, state) 