"""Tests for the Slurm scheduler executor implementation."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import AsyncMock, Mock, patch, call

from benchpro.core.executor.slurm import SlurmExecutor
from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.ports.executor import ExecutionError, ResourceError

@pytest.fixture
def valid_task_data(tmp_path: Path) -> dict:
    """Create valid task data for testing."""
    working_dir = tmp_path / "work"
    working_dir.mkdir()
    template = tmp_path / "job.sh"
    template.parent.mkdir(exist_ok=True)
    template.write_text("#!/bin/bash\necho 'test'\nsleep 1")
    template.chmod(0o755)
    
    return {
        "name": "test_task",
        "working_dir": working_dir,
        "template_path": template,
        "variables": {
            "cores": 4,
            "memory": "8G",
            "walltime": "1:00:00",
            "nodes": 1
        },
    }

@pytest.fixture
def valid_job_data(tmp_path: Path, valid_task_data: dict) -> dict:
    """Create valid job data for testing."""
    working_dir = tmp_path / "job"
    working_dir.mkdir()
    
    task = Task(**valid_task_data)
    resources = {
        "cores": 4,
        "memory": "8G",
        "walltime": "1:00:00",
        "nodes": 1
    }
    
    return {
        "name": "test_job",
        "working_dir": working_dir,
        "tasks": [task],
        "resources": resources,
    }

@pytest.fixture
def slurm_executor(tmp_path):
    """Create a Slurm executor instance."""
    return SlurmExecutor(tmp_path)

@pytest.fixture
def job(valid_job_data):
    """Create a job instance for testing."""
    return Job(**valid_job_data)

@pytest.fixture
def mock_slurm_commands(mocker):
    """Mock Slurm commands."""
    # Create mock commands
    mock_sbatch = mocker.AsyncMock()
    mock_sbatch.communicate.return_value = (b"Submitted batch job 123456\n", b"")
    mock_sbatch.returncode = 0

    mock_squeue = mocker.AsyncMock()
    mock_squeue.communicate.return_value = (b"RUNNING\n", b"")
    mock_squeue.returncode = 0

    mock_scancel = mocker.AsyncMock()
    mock_scancel.communicate.return_value = (b"", b"")
    mock_scancel.returncode = 0

    mock_sacct = mocker.AsyncMock()
    mock_sacct.communicate.return_value = (b"123456|COMPLETED|0:0\n", b"")
    mock_sacct.returncode = 0

    mock_sstat = mocker.AsyncMock()
    mock_sstat.communicate.return_value = (b"1024K|2048K|00:00:30\n", b"")
    mock_sstat.returncode = 0

    # Store command arguments
    command_args = {}

    # Patch the commands
    async def mock_exec_impl(*args, **kwargs):
        command = args[0]
        command_args[command] = args
        if command == "sbatch":
            return mock_sbatch
        elif command == "squeue":
            return mock_squeue
        elif command == "scancel":
            return mock_scancel
        elif command == "sacct":
            return mock_sacct
        elif command == "sstat":
            return mock_sstat
        raise ValueError(f"Unexpected command: {command}")
    
    # Apply the patch
    mocker.patch("asyncio.create_subprocess_exec", side_effect=mock_exec_impl)
    
    return {
        "sbatch": mock_sbatch,
        "squeue": mock_squeue,
        "scancel": mock_scancel,
        "sacct": mock_sacct,
        "sstat": mock_sstat,
        "args": command_args
    }

@pytest.mark.asyncio
async def test_submit_to_scheduler(slurm_executor, job, mock_slurm_commands):
    """Test job submission to Slurm."""
    script_path = job.working_dir / "job.sh"
    script_path.write_text("#!/bin/bash\necho test")

    job_id = await slurm_executor._submit_to_scheduler(job, script_path)
    assert job_id == "123456"

    # Verify sbatch command
    sbatch_args = mock_slurm_commands["args"]["sbatch"]
    assert sbatch_args[0] == "sbatch"
    assert sbatch_args[1] == str(script_path)

@pytest.mark.asyncio
async def test_submit_to_scheduler_failure(slurm_executor, job, mock_slurm_commands):
    """Test handling of sbatch failure."""
    mock_slurm_commands["sbatch"].returncode = 1
    mock_slurm_commands["sbatch"].communicate.return_value = (b"", b"sbatch: error")
    
    script_path = job.working_dir / "job.sh"
    script_path.write_text("#!/bin/bash\necho test")
    
    with pytest.raises(ExecutionError, match="sbatch failed"):
        await slurm_executor._submit_to_scheduler(job, script_path)

@pytest.mark.asyncio
async def test_get_scheduler_job_status(slurm_executor, mock_slurm_commands):
    """Test getting job status from Slurm."""
    status = await slurm_executor._get_scheduler_job_status("123456")
    assert status == "running"

    # Verify squeue command was called correctly
    squeue_args = mock_slurm_commands["args"]["squeue"]
    assert squeue_args[0:5] == ("squeue", "-h", "-o", "%T", "-j")
    assert squeue_args[5] == "123456"

@pytest.mark.asyncio
async def test_get_scheduler_job_status_completed(slurm_executor, mock_slurm_commands):
    """Test getting status of completed job."""
    # Mock squeue to return empty (job not found in queue)
    mock_slurm_commands["squeue"].communicate.return_value = (b"", b"")
    mock_slurm_commands["squeue"].returncode = 0

    # Mock sacct to return completion status
    mock_slurm_commands["sacct"].communicate.return_value = (b"123456|COMPLETED|0:0\n", b"")

    status = await slurm_executor._get_scheduler_job_status("123456")
    assert status == "completed"

    # Verify both commands were called correctly
    squeue_args = mock_slurm_commands["args"]["squeue"]
    sacct_args = mock_slurm_commands["args"]["sacct"]
    assert squeue_args[0:5] == ("squeue", "-h", "-o", "%T", "-j")
    assert squeue_args[5] == "123456"
    assert sacct_args[0:7] == ("sacct", "-n", "-P", "-j", "123456", "-o", "JobID,State,ExitCode")

@pytest.mark.asyncio
async def test_cancel_scheduler_job(slurm_executor, mock_slurm_commands):
    """Test job cancellation in Slurm."""
    await slurm_executor._cancel_scheduler_job("123456")

    # Verify scancel command
    scancel_args = mock_slurm_commands["args"]["scancel"]
    assert scancel_args[0] == "scancel"
    assert scancel_args[1] == "123456"

@pytest.mark.asyncio
async def test_cancel_scheduler_job_failure(slurm_executor, mock_slurm_commands):
    """Test handling of scancel failure."""
    mock_slurm_commands["scancel"].returncode = 1
    mock_slurm_commands["scancel"].communicate.return_value = (b"", b"scancel: error")
    
    with pytest.raises(ExecutionError, match="Failed to cancel job.*scancel: error"):
        await slurm_executor._cancel_scheduler_job("123456")

def test_translate_resources(slurm_executor, job):
    """Test translation of BenchPRO resources to Slurm directives."""
    directives = slurm_executor._translate_resources(job)
    
    assert directives["--nodes"] == "1"
    assert directives["--ntasks-per-node"] == "4"
    assert directives["--mem"] == "8G"
    assert directives["--time"] == "1:00:00"

def test_translate_resources_with_optional_fields(slurm_executor, job):
    """Test resource translation with optional fields."""
    # Add optional resource specifications
    job.resources.update({
        "partition": "debug",
        "qos": "normal",
        "account": "project123"
    })
    
    directives = slurm_executor._translate_resources(job)
    
    assert directives["--partition"] == "debug"
    assert directives["--qos"] == "normal"
    assert directives["--account"] == "project123"

@pytest.mark.asyncio
async def test_job_script_generation(slurm_executor, job, mock_slurm_commands):
    """Test Slurm job script generation."""
    await slurm_executor.submit_job(job)

    # Verify job script was created
    script_path = job.working_dir / "job.sh"
    assert script_path.exists()

    # Verify script contents
    script_contents = script_path.read_text()
    assert "#!/bin/bash" in script_contents
    assert "#SBATCH" in script_contents
    assert job.name in script_contents

    # Verify sbatch command was called correctly
    sbatch_args = mock_slurm_commands["args"]["sbatch"]
    assert sbatch_args[0] == "sbatch"
    assert sbatch_args[1] == str(script_path)

    # Verify job state was updated
    assert job.state == JobState.RUNNING

@pytest.mark.asyncio
async def test_status_mapping(slurm_executor, mock_slurm_commands):
    """Test mapping of Slurm job states to BenchPRO states."""
    status_tests = [
        ("PENDING", JobState.QUEUED),
        ("RUNNING", JobState.RUNNING),
        ("COMPLETED", JobState.COMPLETED),
        ("FAILED", JobState.FAILED),
        ("CANCELLED", JobState.CANCELLED),
        ("TIMEOUT", JobState.FAILED),
    ]

    for slurm_status, expected_state in status_tests:
        mock_slurm_commands["squeue"].communicate.return_value = (slurm_status.encode() + b"\n", b"")
        status = await slurm_executor._get_scheduler_job_status("123456")
        assert status == expected_state.value

@pytest.mark.asyncio
async def test_resource_validation(slurm_executor, job):
    """Test Slurm-specific resource validation."""
    # Test with valid resources
    assert await slurm_executor.validate_resources(job)
    
    # Test with invalid memory format
    job.resources["memory"] = "invalid"
    with pytest.raises(ResourceError, match="Invalid memory format"):
        await slurm_executor.validate_resources(job)
    
    # Test with invalid walltime
    job.resources["memory"] = "8G"  # Reset memory
    job.resources["walltime"] = "invalid"
    with pytest.raises(ResourceError, match="Invalid walltime format"):
        await slurm_executor.validate_resources(job)

@pytest.mark.asyncio
async def test_environment_variables(slurm_executor, job, mock_slurm_commands):
    """Test handling of environment variables in job script."""
    # Add environment variables
    slurm_executor.env = {
        "SLURM_ACCOUNT": "myproject",
        "SLURM_PARTITION": "debug"
    }
    
    await slurm_executor.submit_job(job)
    
    script_path = job.working_dir / "job.sh"
    assert script_path.exists()
    
    content = script_path.read_text()
    # Check for environment variables
    assert "export SLURM_ACCOUNT=myproject" in content
    assert "export SLURM_PARTITION=debug" in content 

@pytest.mark.asyncio
async def test_get_scheduler_job_status_not_found(slurm_executor, mock_slurm_commands):
    """Test handling of non-existent job."""
    # Mock both squeue and sacct to return empty
    mock_slurm_commands["squeue"].communicate.return_value = (b"", b"")
    mock_slurm_commands["squeue"].returncode = 0
    mock_slurm_commands["sacct"].communicate.return_value = (b"", b"")
    mock_slurm_commands["sacct"].returncode = 0

    with pytest.raises(ExecutionError, match="Job 123456 not found"):
        await slurm_executor._get_scheduler_job_status("123456")

@pytest.mark.asyncio
async def test_get_scheduler_job_status_sacct_error(slurm_executor, mock_slurm_commands):
    """Test handling of sacct command failure."""
    # Mock squeue to return empty and sacct to fail
    mock_slurm_commands["squeue"].communicate.return_value = (b"", b"")
    mock_slurm_commands["squeue"].returncode = 0
    mock_slurm_commands["sacct"].communicate.return_value = (b"", b"sacct: error")
    mock_slurm_commands["sacct"].returncode = 1

    with pytest.raises(ExecutionError, match="Failed to get job status"):
        await slurm_executor._get_scheduler_job_status("123456")

@pytest.mark.asyncio
async def test_get_resource_usage_parsing_error(slurm_executor, job, mock_slurm_commands):
    """Test handling of invalid sstat output format."""
    # Add job ID mapping
    slurm_executor._job_ids[job.id] = "123456"
    
    # Mock sstat to return invalid format
    mock_slurm_commands["sstat"].communicate.return_value = (b"invalid|format", b"")
    mock_slurm_commands["sstat"].returncode = 0

    with pytest.raises(ExecutionError, match="Failed to parse sstat output"):
        await slurm_executor.get_resource_usage(job)

@pytest.mark.asyncio
async def test_get_resource_usage_complex_time(slurm_executor, job, mock_slurm_commands):
    """Test parsing of complex CPU time formats."""
    # Add job ID mapping
    slurm_executor._job_ids[job.id] = "123456"
    
    # Test with days-hours:minutes:seconds format
    mock_slurm_commands["sstat"].communicate.return_value = (b"1024K|2048K|2-12:34:56", b"")
    mock_slurm_commands["sstat"].returncode = 0

    usage = await slurm_executor.get_resource_usage(job)
    assert usage["memory_mb"] == 1.0  # 1024K = 1MB
    assert usage["virtual_memory_mb"] == 2.0  # 2048K = 2MB
    assert usage["cpu_time"] == (2 * 24 * 3600) + (12 * 3600) + (34 * 60) + 56

@pytest.mark.asyncio
async def test_submit_job_with_empty_script(slurm_executor, job, mock_slurm_commands):
    """Test handling of empty job script."""
    # Create empty script
    script_path = job.working_dir / "job.sh"
    script_path.write_text("")

    # Mock sbatch to fail with appropriate error
    mock_slurm_commands["sbatch"].returncode = 1
    mock_slurm_commands["sbatch"].communicate.return_value = (b"", b"sbatch: error: invalid script")

    with pytest.raises(ExecutionError, match="sbatch failed: sbatch: error: invalid script"):
        await slurm_executor._submit_to_scheduler(job, script_path)

@pytest.mark.asyncio
async def test_submit_job_with_invalid_job_id(slurm_executor, job, mock_slurm_commands):
    """Test handling of unparseable job ID in sbatch output."""
    # Create script path
    script_path = job.working_dir / "job.sh"
    script_path.write_text("#!/bin/bash\necho test")
    
    # Mock sbatch to return invalid job ID format
    mock_slurm_commands["sbatch"].communicate.return_value = (b"Invalid job ID format\n", b"")
    mock_slurm_commands["sbatch"].returncode = 0

    with pytest.raises(ExecutionError, match="Could not parse job ID from sbatch output"):
        await slurm_executor._submit_to_scheduler(job, script_path)

@pytest.mark.asyncio
async def test_simulator_ssh_connection(slurm_executor, mocker, tmp_path):
    """Test Slurm simulator connection via SSH."""
    # Mock settings to enable simulator with SSH
    settings_mock = mocker.patch.object(slurm_executor, '_settings')
    settings_mock.get.side_effect = lambda key, default=None: {
        "use_slurm_simulator": True,
        "slurm_simulator": {
            "connection_type": "ssh",
            "host": "slurm-sim",
            "port": 2222,
            "username": "simuser",
            "key_file": "/path/to/key.pem"
        }
    }.get(key, default)
    
    # Mock subprocess
    mock_proc = mocker.AsyncMock()
    mock_proc.communicate.return_value = (b"Submitted batch job 123456\n", b"")
    mock_proc.returncode = 0
    
    mock_exec = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
    
    # Create job script
    script_path = tmp_path / "job.sh"
    script_path.write_text("#!/bin/bash\necho test")
    
    # Test submitting a job
    await slurm_executor._submit_to_scheduler(mocker.Mock(), script_path)
    
    # Verify SSH command construction
    mock_exec.assert_called_once()
    args = mock_exec.call_args[0]
    assert args[0] == "ssh"
    assert args[1:5] == ("-p", "2222", "-i", "/path/to/key.pem")
    assert args[5] == "simuser@slurm-sim"
    assert args[6] == "sbatch"
    assert args[7] == str(script_path)

@pytest.mark.asyncio
async def test_simulator_docker_connection(slurm_executor, mocker):
    """Test Slurm simulator connection via Docker."""
    # Mock settings to enable simulator with Docker
    settings_mock = mocker.patch.object(slurm_executor, '_settings')
    settings_mock.get.side_effect = lambda key, default=None: {
        "use_slurm_simulator": True,
        "slurm_simulator": {
            "connection_type": "docker",
            "host": "slurm-sim-container",
            "env_vars": {"SLURM_CONF": "/etc/slurm/slurm.conf"}
        }
    }.get(key, default)
    
    # Mock subprocess
    mock_proc = mocker.AsyncMock()
    mock_proc.communicate.return_value = (b"RUNNING\n", b"")
    mock_proc.returncode = 0
    
    mock_exec = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
    
    # Test getting job status
    await slurm_executor._get_scheduler_job_status("123456")
    
    # Verify Docker command construction
    mock_exec.assert_called()
    args = mock_exec.call_args[0]
    assert args[0:3] == ("docker", "exec", "slurm-sim-container")
    assert args[3:7] == ("squeue", "-h", "-o", "%T")
    assert args[7:9] == ("-j", "123456")
    
    # Verify environment variables
    env = mock_exec.call_args[1]["env"]
    assert env["SLURM_CONF"] == "/etc/slurm/slurm.conf"

@pytest.mark.asyncio
async def test_simulator_local_connection(slurm_executor, mocker):
    """Test Slurm simulator with local connection."""
    # Mock settings to enable simulator with local connection
    settings_mock = mocker.patch.object(slurm_executor, '_settings')
    settings_mock.get.side_effect = lambda key, default=None: {
        "use_slurm_simulator": True,
        "slurm_simulator": {
            "connection_type": "local",
            "env_vars": {
                "SLURM_SIMULATOR": "1",
                "SLURM_SIM_PATH": "/opt/slurm-sim"
            }
        }
    }.get(key, default)
    
    # Mock subprocess
    mock_proc = mocker.AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0
    
    mock_exec = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
    
    # Test canceling a job
    await slurm_executor._cancel_scheduler_job("123456")
    
    # Verify command is executed locally with environment
    mock_exec.assert_called_once()
    args = mock_exec.call_args[0]
    assert args[0:2] == ("scancel", "123456")
    
    # Verify environment variables
    env = mock_exec.call_args[1]["env"]
    assert env["SLURM_SIMULATOR"] == "1"
    assert env["SLURM_SIM_PATH"] == "/opt/slurm-sim"

@pytest.mark.asyncio
async def test_simulator_connection_error(slurm_executor, mocker, tmp_path):
    """Test handling of simulator connection errors."""
    # Mock settings to enable simulator
    settings_mock = mocker.patch.object(slurm_executor, '_settings')
    settings_mock.get.side_effect = lambda key, default=None: {
        "use_slurm_simulator": True,
        "slurm_simulator": {
            "connection_type": "ssh",
            "host": "slurm-sim"
        }
    }.get(key, default)
    
    # Create job script
    script_path = tmp_path / "job.sh"
    script_path.write_text("#!/bin/bash\necho test")
    
    # Mock subprocess to raise connection error
    mock_exec = mocker.patch("asyncio.create_subprocess_exec", 
                            side_effect=ConnectionError("Connection refused"))
    
    # Test error handling
    with pytest.raises(ExecutionError, match="Failed to execute sbatch: Connection refused"):
        await slurm_executor._submit_to_scheduler(mocker.Mock(), script_path)
        
    mock_exec.assert_called_once()

@pytest.mark.asyncio
async def test_simulator_disabled(slurm_executor, mocker, tmp_path):
    """Test that commands are executed directly when simulator is disabled."""
    # Mock settings to disable simulator
    settings_mock = mocker.patch.object(slurm_executor, '_settings')
    settings_mock.get.return_value = False

    # Mock subprocess
    mock_proc = mocker.AsyncMock()
    mock_proc.communicate.return_value = (b"Submitted batch job 123456\n", b"")
    mock_proc.returncode = 0

    mock_exec = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

    # Create job script
    script_path = tmp_path / "job.sh"
    script_path.write_text("#!/bin/bash\necho test")

    # Test command execution
    job_id = await slurm_executor._submit_to_scheduler(mocker.Mock(), script_path)
    
    # Verify job ID was parsed correctly
    assert job_id == "123456"
    
    # Verify command was executed directly
    mock_exec.assert_called_once_with(
        "sbatch", str(script_path),
        stdout=mocker.ANY,
        stderr=mocker.ANY,
        env=mocker.ANY
    )

@pytest.mark.asyncio
async def test_simulator_lima_connection(slurm_executor, mocker):
    """Test Slurm simulator connection via Lima."""
    # Mock settings to enable simulator with Lima
    settings_mock = mocker.patch.object(slurm_executor, '_settings')
    settings_mock.get.side_effect = lambda key, default=None: {
        "use_slurm_simulator": True,
        "slurm_simulator": {
            "connection_type": "lima",
            "instance": "slurm",
            "env_vars": {"SLURM_CONF": "/etc/slurm/slurm.conf"}
        }
    }.get(key, default)
    
    # Mock subprocess
    mock_proc = mocker.AsyncMock()
    mock_proc.communicate.return_value = (b"RUNNING\n", b"")
    mock_proc.returncode = 0
    
    mock_exec = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
    
    # Test getting job status
    await slurm_executor._get_scheduler_job_status("123456")
    
    # Verify Lima command construction
    mock_exec.assert_called()
    args = mock_exec.call_args[0]
    assert args[0:4] == ("limactl", "shell", "slurm", "squeue")
    assert args[4:8] == ("-h", "-o", "%T", "-j")
    assert args[8] == "123456"
    
    # Verify environment variables
    env = mock_exec.call_args[1]["env"]
    assert env["SLURM_CONF"] == "/etc/slurm/slurm.conf" 