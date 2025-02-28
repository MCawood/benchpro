# Slurm Integration Plan

## Project Overview

BenchPRO is extending its execution capabilities to support HPC job schedulers, starting with Slurm integration. This document outlines the architecture, implementation plan, and testing strategy based on existing test implementations.

## Core Components

### 1. Task Domain
The `Task` class represents a unit of work with:
- Name and working directory
- Template script for execution
- State management (CREATED → RUNNING → COMPLETED/FAILED)
- Resource requirements (cores, memory, etc.)
- File staging capabilities

### 2. Job Scheduler Architecture
```
Executor (Base)
├── LocalExecutor
└── SchedulerExecutor (Abstract)
    └── SlurmExecutor
```

### 3. Testing Infrastructure
- Local Slurm simulator in Docker container
- Provides realistic HPC environment for testing
- Accessible via wrapper scripts in `/Users/mcawood/dev/slurm_sim`

## Implementation Plan

### 1. Scheduler Base Class

```python
class SchedulerExecutor(Executor):
    """Base class for job scheduler executors."""
    
    async def _submit_to_scheduler(self, job: Job, script_path: Path) -> str:
        """Submit job to scheduler, return job ID."""
        raise NotImplementedError
        
    async def _cancel_scheduler_job(self, scheduler_job_id: str) -> None:
        """Cancel a running job."""
        raise NotImplementedError
        
    async def _get_scheduler_job_status(self, scheduler_job_id: str) -> str:
        """Get current job status."""
        raise NotImplementedError
        
    def _translate_resources(self, job: Job) -> Dict[str, str]:
        """Convert BenchPRO resources to scheduler directives."""
        raise NotImplementedError
```

### 2. Slurm Implementation

The `SlurmExecutor` class implements:

1. **Job Submission**
```python
async def _submit_to_scheduler(self, job: Job, script_path: Path) -> str:
    """Submit job using sbatch, parse job ID from output."""
    proc = await asyncio.create_subprocess_exec(
        "sbatch", str(script_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        raise ExecutionError(f"sbatch failed: {stderr.decode()}")
        
    # Parse "Submitted batch job 123456"
    return stdout.decode().strip().split()[-1]
```

2. **Status Monitoring**
```python
async def _get_scheduler_job_status(self, scheduler_job_id: str) -> str:
    """Check job status using squeue/sacct."""
    # First check squeue for running jobs
    proc = await asyncio.create_subprocess_exec(
        "squeue", "-h", "-o", "%i|%t|%j|", "-j", scheduler_job_id,
        stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    
    if stdout:
        status = stdout.decode().strip().split("|")[1]
        return self._translate_status(status)
        
    # If not in queue, check sacct for completion status
    proc = await asyncio.create_subprocess_exec(
        "sacct", "-n", "-P", "-j", scheduler_job_id, "-o", "JobID,State,ExitCode",
        stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return self._translate_status(stdout.decode().strip().split("|")[1])
```

3. **Resource Translation**
```python
def _translate_resources(self, job: Job) -> Dict[str, str]:
    """Convert BenchPRO resources to Slurm directives."""
    directives = {
        "--nodes": str(job.resources["nodes"]),
        "--ntasks-per-node": str(job.resources["cores"]),
        "--mem": job.resources["memory"],
        "--time": job.resources["walltime"]
    }
    
    # Optional specifications
    for slurm_opt, res_key in [
        ("--partition", "partition"),
        ("--qos", "qos"),
        ("--account", "account")
    ]:
        if res_key in job.resources:
            directives[slurm_opt] = job.resources[res_key]
            
    return directives
```

### 3. State Mapping
```python
SLURM_TO_JOB_STATE = {
    "PENDING": JobState.QUEUED,
    "RUNNING": JobState.RUNNING,
    "COMPLETED": JobState.COMPLETED,
    "FAILED": JobState.FAILED,
    "CANCELLED": JobState.CANCELLED,
    "TIMEOUT": JobState.FAILED
}
```

## Development Phases

### Phase 1: Core Implementation
1. Implement `SlurmExecutor` base functionality
   - Job submission with proper error handling
   - Status monitoring with state translation
   - Resource validation and translation
   - Job script generation with Slurm directives

### Phase 2: Testing
1. Unit tests with mocked Slurm commands
2. Integration tests with actual Slurm environment
3. Error handling and recovery tests
4. Resource validation tests

### Phase 3: Advanced Features
1. Job array support
2. Advanced resource specifications
3. Environment variable handling
4. Job script templating

## Testing Strategy

### 1. Unit Tests
Based on `test_slurm.py`:

```python
@pytest.mark.asyncio
async def test_submit_to_scheduler(slurm_executor, job, mock_slurm_commands):
    """Test job submission to Slurm."""
    script_path = job.working_dir / "job.sh"
    script_path.write_text("#!/bin/bash\necho test")
    
    job_id = await slurm_executor._submit_to_scheduler(job, script_path)
    assert job_id == "123456"
```

### 2. Error Handling
```python
@pytest.mark.asyncio
async def test_submit_to_scheduler_failure(slurm_executor, job, mock_slurm_commands):
    """Test handling of sbatch failure."""
    mock_slurm_commands["sbatch"].returncode = 1
    mock_slurm_commands["sbatch"].communicate.return_value = (b"", b"sbatch: error")
    
    with pytest.raises(ExecutionError, match="sbatch failed"):
        await slurm_executor._submit_to_scheduler(job, script_path)
```

### 3. Resource Validation
```python
@pytest.mark.asyncio
async def test_resource_validation(slurm_executor, job):
    """Test Slurm-specific resource validation."""
    # Test with valid resources
    assert await slurm_executor.validate_resources(job)
    
    # Test with invalid memory format
    job.resources["memory"] = "invalid"
    with pytest.raises(ResourceError):
        await slurm_executor.validate_resources(job)
```

## Development Phases

### Phase 1: Core Implementation
1. Implement `SlurmExecutor` base functionality
   - Job submission with proper error handling
   - Status monitoring with state translation
   - Resource validation and translation
   - Job script generation with Slurm directives

### Phase 2: Testing
1. Unit tests with mocked Slurm commands
2. Integration tests with actual Slurm environment
3. Error handling and recovery tests
4. Resource validation tests

### Phase 3: Advanced Features
1. Job array support
2. Advanced resource specifications
3. Environment variable handling
4. Job script templating

## Error Handling

1. **Submission Errors**
   - Invalid resource requests
   - Script permission issues
   - Queue access problems

2. **Runtime Errors**
   - Job failures
   - Timeout conditions
   - Resource limit violations

3. **System Errors**
   - Scheduler unavailable
   - Network issues
   - File system problems

## Future Considerations

1. **Extensibility**
   - Support for other schedulers (PBS, LSF)
   - Custom resource translators
   - Site-specific configurations

2. **Performance**
   - Job status caching
   - Batch status queries
   - Efficient resource monitoring

3. **Security**
   - Credential management
   - Job script sanitization
   - Resource limits enforcement 