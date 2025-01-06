"""Local executor implementation."""

import asyncio
import os
import signal
from pathlib import Path
from typing import Dict, List, Optional

import psutil

from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.ports.executor import Executor, ExecutionError, ResourceError


class LocalExecutor(Executor):
    """Executes jobs on the local machine."""

    def __init__(self):
        """Initialize the local executor."""
        self._running_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._task_monitors: Dict[str, asyncio.Task] = {}

    async def validate_resources(self, job: Job) -> None:
        """Validate that the local machine has sufficient resources for the job."""
        # Check CPU cores
        available_cores = psutil.cpu_count()
        if job.resources.cores > available_cores:
            raise ResourceError(
                f"Requested {job.resources.cores} cores but only {available_cores} available"
            )

        # Check memory
        memory_bytes = self._parse_memory(job.resources.memory)
        available_memory = psutil.virtual_memory().available
        if memory_bytes > available_memory:
            raise ResourceError(
                f"Requested {job.resources.memory} but only "
                f"{self._format_memory(available_memory)} available"
            )

    async def submit_job(self, job: Job) -> None:
        """Submit a job for execution on the local machine."""
        try:
            await self.validate_resources(job)
            job.state = JobState.RUNNING

            for task in job.tasks:
                await self._execute_task(task)

        except Exception as e:
            job.state = JobState.FAILED
            raise ExecutionError(f"Failed to submit job: {str(e)}") from e

    async def cancel_job(self, job: Job) -> None:
        """Cancel a running job."""
        job.state = JobState.CANCELLED
        for task in job.tasks:
            if task.state == TaskState.RUNNING:
                task.state = TaskState.CANCELLED
                await self._terminate_task(task)

    async def get_job_status(self, job: Job) -> Dict:
        """Get the current status of a job."""
        task_counts = {
            "total": len(job.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

        for task in job.tasks:
            task_counts[task.state.value.lower()] += 1

        return {
            "state": job.state.value.lower(),
            "tasks": task_counts,
        }

    async def get_resource_usage(self, job: Job) -> Dict:
        """Get the current resource usage of a job."""
        total_cpu = 0.0
        total_memory = 0
        total_io_read = 0
        total_io_write = 0

        for task in job.tasks:
            if task.state == TaskState.RUNNING and task.name in self._running_processes:
                process = psutil.Process(self._running_processes[task.name].pid)
                try:
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_info = process.memory_info()
                    io_counters = process.io_counters()

                    total_cpu += cpu_percent
                    total_memory += memory_info.rss
                    total_io_read += io_counters.read_bytes
                    total_io_write += io_counters.write_bytes
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        return {
            "cpu_percent": total_cpu,
            "memory_bytes": total_memory,
            "io_read_bytes": total_io_read,
            "io_write_bytes": total_io_write,
        }

    async def cleanup_job(self, job: Job) -> None:
        """Clean up any resources associated with a job."""
        for task in job.tasks:
            if task.state == TaskState.RUNNING:
                await self._terminate_task(task)

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        try:
            # Ensure working directory exists
            os.makedirs(task.working_dir, exist_ok=True)

            # Create process
            process = await asyncio.create_subprocess_exec(
                str(task.template_path),
                cwd=task.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._running_processes[task.name] = process
            task.state = TaskState.RUNNING

            # Start monitoring task
            monitor = asyncio.create_task(self._monitor_task(task, process))
            self._task_monitors[task.name] = monitor

        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            raise ExecutionError(f"Failed to execute task: {str(e)}") from e

    async def _monitor_task(self, task: Task, process: asyncio.subprocess.Process) -> None:
        """Monitor a task's execution."""
        try:
            stdout, stderr = await process.communicate()
            return_code = process.returncode

            # Don't update state if task was cancelled
            if task.state != TaskState.CANCELLED:
                if return_code == 0:
                    task.state = TaskState.COMPLETED
                else:
                    task.state = TaskState.FAILED
                    task.error = f"Task failed with return code {return_code}\n"
                    if stderr:
                        task.error += stderr.decode()

            # Cleanup
            if task.name in self._running_processes:
                del self._running_processes[task.name]
            if task.name in self._task_monitors:
                del self._task_monitors[task.name]

        except asyncio.CancelledError:
            # Task monitor was cancelled, don't update state
            pass
        except Exception as e:
            if task.state != TaskState.CANCELLED:
                task.state = TaskState.FAILED
                task.error = str(e)
            if task.name in self._running_processes:
                del self._running_processes[task.name]
            if task.name in self._task_monitors:
                del self._task_monitors[task.name]

    async def _terminate_task(self, task: Task) -> None:
        """Terminate a running task."""
        if task.name in self._running_processes:
            process = self._running_processes[task.name]
            try:
                # Handle terminate as a coroutine
                terminate = process.terminate()
                if asyncio.iscoroutine(terminate):
                    await terminate
                await process.wait()
            except ProcessLookupError:
                pass
            finally:
                if task.name in self._running_processes:
                    del self._running_processes[task.name]
                if task.name in self._task_monitors:
                    monitor = self._task_monitors[task.name]
                    monitor.cancel()
                    del self._task_monitors[task.name]

    def _parse_memory(self, memory_str: str) -> int:
        """Parse a memory string (e.g., '8G') into bytes."""
        units = {
            'K': 1024,
            'M': 1024 ** 2,
            'G': 1024 ** 3,
            'T': 1024 ** 4,
        }
        
        if not memory_str:
            return 0
            
        unit = memory_str[-1].upper()
        if unit in units:
            try:
                value = float(memory_str[:-1])
                return int(value * units[unit])
            except ValueError:
                raise ResourceError(f"Invalid memory format: {memory_str}")
        try:
            return int(memory_str)
        except ValueError:
            raise ResourceError(f"Invalid memory format: {memory_str}")

    def _format_memory(self, bytes_value: int) -> str:
        """Format bytes into a human-readable string."""
        for unit in ['', 'K', 'M', 'G', 'T']:
            if bytes_value < 1024:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f}P" 