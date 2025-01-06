Executor System
==============

The executor system is responsible for running jobs and tasks across different execution environments. It provides a consistent interface while allowing for different backend implementations.

Executor Interface
---------------

The base executor interface defines the contract that all executor implementations must follow:

.. code-block:: python

    class Executor(ABC):
        @abstractmethod
        async def validate_resources(self, job: Job) -> None:
            """Validate that required resources are available."""

        @abstractmethod
        async def submit_job(self, job: Job) -> None:
            """Submit a job for execution."""

        @abstractmethod
        async def cancel_job(self, job: Job) -> None:
            """Cancel a running job."""

        @abstractmethod
        async def get_job_status(self, job: Job) -> Dict:
            """Get current status of a job."""

        @abstractmethod
        async def get_resource_usage(self, job: Job) -> Dict:
            """Get current resource usage of a job."""

        @abstractmethod
        async def cleanup_job(self, job: Job) -> None:
            """Clean up resources after job completion."""

Local Executor
------------

The local executor implements the executor interface for running jobs on the local machine:

Key Features:
~~~~~~~~~~~

* **Process Management**: Creates and monitors subprocesses for tasks
* **Resource Validation**: Checks available CPU cores and memory
* **State Tracking**: Maintains task and job states
* **Resource Monitoring**: Tracks CPU, memory, and I/O usage
* **Error Handling**: Comprehensive error reporting

Implementation Details:
~~~~~~~~~~~~~~~~~~~~

Process Management
^^^^^^^^^^^^^^^^

The local executor uses Python's asyncio subprocess functionality:

.. code-block:: python

    async def _execute_task(self, task: Task) -> None:
        process = await asyncio.create_subprocess_exec(
            str(task.template_path),
            cwd=task.working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

Task Monitoring
^^^^^^^^^^^^^

Each task is monitored in a separate coroutine:

.. code-block:: python

    async def _monitor_task(self, task: Task, process: Process) -> None:
        try:
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                task.state = TaskState.COMPLETED
            else:
                task.state = TaskState.FAILED
                task.error = f"Task failed with return code {process.returncode}"

Resource Management
^^^^^^^^^^^^^^^^

Resources are validated before job submission:

.. code-block:: python

    async def validate_resources(self, job: Job) -> None:
        # Check CPU cores
        if job.resources.cores > psutil.cpu_count():
            raise ResourceError("Insufficient CPU cores")

        # Check memory
        memory_bytes = self._parse_memory(job.resources.memory)
        if memory_bytes > psutil.virtual_memory().available:
            raise ResourceError("Insufficient memory")

Error Handling
^^^^^^^^^^^^

The executor provides detailed error information:

* Resource validation errors
* Task execution failures
* Process termination errors
* System resource errors

Usage Example
-----------

Here's how to use the local executor:

.. code-block:: python

    # Create an executor
    executor = LocalExecutor()

    # Create and submit a job
    job = Job(...)
    await executor.submit_job(job)

    # Monitor job status
    status = await executor.get_job_status(job)
    print(f"Job state: {status['state']}")
    print(f"Tasks: {status['tasks']}")

    # Monitor resource usage
    usage = await executor.get_resource_usage(job)
    print(f"CPU usage: {usage['cpu_percent']}%")
    print(f"Memory usage: {usage['memory_bytes']} bytes")

    # Cancel job if needed
    await executor.cancel_job(job)

    # Clean up
    await executor.cleanup_job(job)

Future Extensions
--------------

The executor system is designed for extensibility:

* **SLURM Executor**: For HPC environments
* **Kubernetes Executor**: For container orchestration
* **Cloud Executors**: For various cloud providers
* **Distributed Executor**: For multi-node execution 