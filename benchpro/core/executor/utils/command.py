"""Command execution utilities.

This module provides helper functions for executing commands and handling their output.
"""

import asyncio
import logging
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

async def execute_command(
    cmd: str,
    args: Tuple[str, ...],
    cwd: Optional[Path] = None,
    timeout: Optional[float] = None
) -> Tuple[int, str, str]:
    """Execute a command and return its output.
    
    Args:
        cmd: The command to execute
        args: Command arguments
        cwd: Working directory for command execution
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (return_code, stdout, stderr)
        
    Raises:
        asyncio.TimeoutError: If command execution times out
        OSError: If command execution fails
    """
    try:
        logger.debug("Executing command: %s %s", cmd, " ".join(args))
        
        process = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return (
                process.returncode or 0,
                stdout.decode().strip(),
                stderr.decode().strip()
            )
            
        except asyncio.TimeoutError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            raise
            
    except Exception as e:
        logger.error("Command execution failed: %s", str(e))
        raise

async def execute_shell_command(
    cmd: str,
    cwd: Optional[Path] = None,
    timeout: Optional[float] = None
) -> Tuple[int, str, str]:
    """Execute a shell command and return its output.
    
    Args:
        cmd: The shell command to execute
        cwd: Working directory for command execution
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (return_code, stdout, stderr)
        
    Raises:
        asyncio.TimeoutError: If command execution times out
        OSError: If command execution fails
    """
    try:
        logger.debug("Executing shell command: %s", cmd)
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return (
                process.returncode or 0,
                stdout.decode().strip(),
                stderr.decode().strip()
            )
            
        except asyncio.TimeoutError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            raise
            
    except Exception as e:
        logger.error("Shell command execution failed: %s", str(e))
        raise 