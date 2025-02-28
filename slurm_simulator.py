def get_job_state(self, job_id):
    """Get the current state of a Slurm job.
    
    Args:
        job_id (str): The Slurm job ID to check
        
    Returns:
        str: One of PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    """
    # First check if job is in queue
    stdout, rc = self.execute_slurm_command(f"squeue -j {job_id} -h -o '%T'")
    if rc == 0 and stdout.strip():
        return stdout.strip()
        
    # Check slurmd.log for job completion and exit code
    stdout, rc = self.execute_slurm_command(f"grep -E '\\[{job_id}\\.batch\\]' /var/log/slurmd.log | tail -n1")
    if rc == 0 and stdout.strip():
        if "stepd_cleanup" in stdout and "rc[0x" in stdout:
            # Job failed with non-zero exit code
            return "FAILED"
        elif "done with step" in stdout:
            # Job completed successfully
            return "COMPLETED"
            
    # Check if job was cancelled
    stdout, rc = self.execute_slurm_command(f"grep 'REQUEST_KILL_JOB JobId={job_id}' /var/log/slurmctld.log")
    if rc == 0 and stdout.strip():
        return "CANCELLED"
        
    # If we can't determine state, assume it's still pending
    return "PENDING" 