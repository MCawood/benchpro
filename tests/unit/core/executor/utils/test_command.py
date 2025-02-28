"""Tests for command execution utilities."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from benchpro.core.executor.utils.command import execute_command, execute_shell_command

@pytest.mark.asyncio
async def test_execute_command_success():
    """Test successful command execution."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"stdout", b"stderr")
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        returncode, stdout, stderr = await execute_command(
            "echo",
            ("hello",),
            cwd=Path("/tmp")
        )
        
    assert returncode == 0
    assert stdout == "stdout"
    assert stderr == "stderr"

@pytest.mark.asyncio
async def test_execute_command_failure():
    """Test command execution failure."""
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"error")
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        returncode, stdout, stderr = await execute_command(
            "false",
            (),
            cwd=Path("/tmp")
        )
        
    assert returncode == 1
    assert stdout == ""
    assert stderr == "error"

@pytest.mark.asyncio
async def test_execute_command_timeout():
    """Test command execution timeout."""
    mock_process = AsyncMock()
    mock_process.communicate.side_effect = asyncio.TimeoutError
    mock_process.wait.return_value = None
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(asyncio.TimeoutError):
            await execute_command(
                "sleep",
                ("10",),
                cwd=Path("/tmp"),
                timeout=1
            )
    
    assert mock_process.terminate.called

@pytest.mark.asyncio
async def test_execute_command_kill():
    """Test command termination with kill."""
    mock_process = AsyncMock()
    mock_process.communicate.side_effect = asyncio.TimeoutError
    mock_process.wait.side_effect = asyncio.TimeoutError
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(asyncio.TimeoutError):
            await execute_command(
                "sleep",
                ("10",),
                cwd=Path("/tmp"),
                timeout=1
            )
    
    assert mock_process.terminate.called
    assert mock_process.kill.called

@pytest.mark.asyncio
async def test_execute_shell_command_success():
    """Test successful shell command execution."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"stdout", b"stderr")
    
    with patch("asyncio.create_subprocess_shell", return_value=mock_process):
        returncode, stdout, stderr = await execute_shell_command(
            "echo hello",
            cwd=Path("/tmp")
        )
        
    assert returncode == 0
    assert stdout == "stdout"
    assert stderr == "stderr"

@pytest.mark.asyncio
async def test_execute_shell_command_failure():
    """Test shell command execution failure."""
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"error")
    
    with patch("asyncio.create_subprocess_shell", return_value=mock_process):
        returncode, stdout, stderr = await execute_shell_command(
            "false",
            cwd=Path("/tmp")
        )
        
    assert returncode == 1
    assert stdout == ""
    assert stderr == "error"

@pytest.mark.asyncio
async def test_execute_shell_command_timeout():
    """Test shell command execution timeout."""
    mock_process = AsyncMock()
    mock_process.communicate.side_effect = asyncio.TimeoutError
    mock_process.wait.return_value = None
    
    with patch("asyncio.create_subprocess_shell", return_value=mock_process):
        with pytest.raises(asyncio.TimeoutError):
            await execute_shell_command(
                "sleep 10",
                cwd=Path("/tmp"),
                timeout=1
            )
    
    assert mock_process.terminate.called

@pytest.mark.asyncio
async def test_execute_shell_command_kill():
    """Test shell command termination with kill."""
    mock_process = AsyncMock()
    mock_process.communicate.side_effect = asyncio.TimeoutError
    mock_process.wait.side_effect = asyncio.TimeoutError
    
    with patch("asyncio.create_subprocess_shell", return_value=mock_process):
        with pytest.raises(asyncio.TimeoutError):
            await execute_shell_command(
                "sleep 10",
                cwd=Path("/tmp"),
                timeout=1
            )
    
    assert mock_process.terminate.called
    assert mock_process.kill.called 