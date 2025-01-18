"""Local executor implementation for BenchPRO.

This module provides a local executor that runs tasks on the local machine
using subprocess and asyncio.
"""

import asyncio
import os
import psutil
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from .base import Executor, ExecutorError, TaskExecutionError, ResourceError
from benchpro.core.domain import Task, TaskState

class LocalExecutor(Executor):
    """Execute tasks on the local machine.
    
    This executor runs tasks as subprocesses on the local system.
    It monitors resource usage and enforces resource limits.
    """
    
    def __init__(self, working_dir: Path, env: Optional[Dict[str, str]] = None):
        """Initialize the local executor.
        
        Args:
            working_dir: Base directory for executor operations
            env: Optional environment variables for task execution
        """
        super().__init__(working_dir, env)
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._monitors: Dict[str, asyncio.Task] = {}
    
    async def validate_resources(self, task: Task) -> bool:
        """Validate that required resources are available locally.
        
        Args:
            task: The task to validate resources for
            
        Returns:
            True if resources are available, False otherwise
            
        Raises:
            ResourceError: If resource validation fails
        """
        try:
            # Check CPU cores
            required_cores = task.variables.get('cores', 1)
            available_cores = psutil.cpu_count()
            if required_cores > available_cores:
                raise ResourceError(
                    f"Not enough CPU cores. Required: {required_cores}, Available: {available_cores}"
                )
            
            # Check memory
            memory_str = task.variables.get('memory', '1G')
            required_memory = self._parse_memory(memory_str)
            available_memory = psutil.virtual_memory().available
            if required_memory > available_memory:
                raise ResourceError(
                    f"Not enough memory. Required: {memory_str}, "
                    f"Available: {self._format_memory(available_memory)}"
                )
            
            # Check disk space
            required_space = task.variables.get('disk_space', 1024 * 1024 * 1024)  # Default 1GB
            available_space = shutil.disk_usage(task.working_dir).free
            if required_space > available_space:
                raise ResourceError(
                    f"Not enough disk space. Required: {required_space}, "
                    f"Available: {available_space}"
                )
            
            return True
            
        except Exception as e:
            raise ResourceError(f"Resource validation failed: {str(e)}")
    
    async def prepare(self, task: Task) -> None:
        """Prepare the local execution environment.
        
        Args:
            task: The task to prepare for execution
            
        Raises:
            ExecutorError: If preparation fails
        """
        try:
            # Create working directory
            task.working_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy template if provided
            if task.template_path:
                script_path = task.working_dir / "run.sh"
                shutil.copy2(task.template_path, script_path)
                script_path.chmod(0o755)  # Make executable
            
            # Create environment file
            env_file = task.working_dir / "env.sh"
            env_vars = {
                **self.env,
                'BENCHPRO_TASK_NAME': task.name,
                'BENCHPRO_TASK_DIR': str(task.working_dir),
                'BENCHPRO_CORES': str(task.variables.get('cores', 1)),
                'BENCHPRO_MEMORY': task.variables.get('memory', '1G'),
                'BENCHPRO_WALLTIME': str(task.variables.get('walltime', 3600))
            }
            env_content = '\n'.join(f'export {k}="{v}"' for k, v in env_vars.items())
            env_file.write_text(env_content)
            
        except Exception as e:
            raise ExecutorError(f"Failed to prepare task environment: {str(e)}")
    
    async def run(self, task: Task) -> None:
        """Execute a task locally.
        
        Args:
            task: The task to execute
            
        Raises:
            TaskExecutionError: If task execution fails
        """
        try:
            # Validate resources first
            await self.validate_resources(task)

            # Prepare environment and transition through states
            task.transition_to(TaskState.STAGING)
            await self.prepare(task)
            task.transition_to(TaskState.PENDING)

            # Build command
            cmd = []
            if task.template_path:
                cmd = ['bash', str(task.working_dir / "run.sh")]
            else:
                raise TaskExecutionError("No template script provided")

            # Start process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(task.working_dir),
                env=os.environ.copy()
            )

            self._processes[task.name] = process
            task.transition_to(TaskState.RUNNING)

            # Start monitoring
            monitor = asyncio.create_task(self._monitor_task(task))
            self._monitors[task.name] = monitor

            # Wait for completion
            stdout, stderr = await process.communicate()

            # Only treat explicitly non-zero returncodes as failures
            if process.returncode is not None:
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    task.transition_to(TaskState.FAILED, error_msg)
                    raise TaskExecutionError(f"Task failed with exit code {process.returncode}\nStderr: {error_msg}")
                else:
                    task.transition_to(TaskState.COMPLETED)

        except Exception as e:
            # Only transition to FAILED if we're not in a terminal state
            if task.state not in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                task.transition_to(TaskState.FAILED, str(e))
            raise TaskExecutionError(f"Failed to start task: {str(e)}")
    
    async def status(self, task: Task) -> TaskState:
        """Get the current status of a task.
        
        Args:
            task: The task to check status for
            
        Returns:
            The current state of the task
        """
        process = self._processes.get(task.name)
        if not process:
            return task.state
        
        # Ensure proper state transitions
        if process.returncode is None:
            # Transition to RUNNING through PENDING if needed
            if task.state == TaskState.CREATED:
                task.transition_to(TaskState.PENDING)
            if task.state == TaskState.PENDING:
                task.transition_to(TaskState.RUNNING)
            return TaskState.RUNNING
        elif process.returncode == 0:
            # Transition to COMPLETED through proper states
            if task.state == TaskState.CREATED:
                task.transition_to(TaskState.PENDING)
            if task.state == TaskState.PENDING:
                task.transition_to(TaskState.RUNNING)
            if task.state == TaskState.RUNNING:
                task.transition_to(TaskState.COMPLETED)
            return TaskState.COMPLETED
        else:
            # Failed state can be reached from any state
            if task.state != TaskState.FAILED:
                task.transition_to(TaskState.FAILED, f"Process exited with code {process.returncode}")
            return TaskState.FAILED
    
    async def stop(self, task: Task) -> None:
        """Stop a running task.
        
        Args:
            task: The task to stop
            
        Raises:
            ExecutorError: If stopping the task fails
        """
        try:
            process = self._processes.get(task.name)
            if process and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            
            monitor = self._monitors.get(task.name)
            if monitor and not monitor.done():
                monitor.cancel()
                try:
                    await monitor
                except asyncio.CancelledError:
                    pass
                
        except Exception as e:
            raise ExecutorError(f"Failed to stop task: {str(e)}")
    
    async def cleanup(self, task: Task) -> None:
        """Clean up after task completion.
        
        Args:
            task: The task to clean up after
            
        Raises:
            ExecutorError: If cleanup fails
        """
        try:
            # Remove process and monitor references
            self._processes.pop(task.name, None)
            self._monitors.pop(task.name, None)
            
            # Archive logs if needed
            stdout_path = task.working_dir / "stdout.log"
            stderr_path = task.working_dir / "stderr.log"
            if stdout_path.exists():
                archive_dir = task.working_dir / "logs"
                archive_dir.mkdir(exist_ok=True)
                shutil.move(stdout_path, archive_dir / "stdout.log")
                shutil.move(stderr_path, archive_dir / "stderr.log")
                
        except Exception as e:
            raise ExecutorError(f"Failed to clean up task: {str(e)}")
    
    async def _monitor_task(self, task: Task) -> None:
        """Monitor a running task.
        
        Args:
            task: The task to monitor
        """
        process = self._processes[task.name]
        try:
            stdout, stderr = await process.communicate()
            
            # Write output to files
            (task.working_dir / "stdout.log").write_bytes(stdout)
            (task.working_dir / "stderr.log").write_bytes(stderr)
            
            # Update task state based on return code
            if process.returncode == 0:
                task.transition_to(TaskState.COMPLETED)
            else:
                error_msg = stderr.decode().strip() or "Unknown error"
                task.transition_to(TaskState.FAILED, error_msg)
            
        except asyncio.CancelledError:
            # Handle cancellation
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
                task.transition_to(TaskState.CANCELLED)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                task.transition_to(TaskState.CANCELLED, "Task was forcefully terminated")
            raise
    
    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to bytes.
        
        Args:
            memory_str: Memory string (e.g., "1G", "512M")
            
        Returns:
            Memory size in bytes
        """
        units = {
            'K': 1024,
            'M': 1024 * 1024,
            'G': 1024 * 1024 * 1024,
            'T': 1024 * 1024 * 1024 * 1024
        }
        
        size = memory_str[:-1]
        unit = memory_str[-1].upper()
        
        try:
            return int(float(size) * units[unit])
        except (ValueError, KeyError):
            raise ValueError(f"Invalid memory format: {memory_str}")
    
    def _format_memory(self, bytes: int) -> str:
        """Format bytes as human-readable string.
        
        Args:
            bytes: Memory size in bytes
            
        Returns:
            Formatted memory string
        """
        for unit in ['', 'K', 'M', 'G', 'T']:
            if bytes < 1024:
                return f"{bytes:.1f}{unit}"
            bytes /= 1024
        return f"{bytes:.1f}P" 