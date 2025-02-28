Job Execution
=============

This guide explains how to execute and manage jobs in BenchPRO.

Basic Execution
-------------

.. code-block:: python

    from benchpro.core.infrastructure import LocalExecutor
    import asyncio

    async def run_job(job):
        executor = LocalExecutor()
        await executor.submit_job(job)
        await monitor_job(executor, job)

Job States
---------

Jobs can be in the following states:

* created (initial state)
* queued
* running
* completed
* failed
* cancelled

State Transitions
--------------

Jobs follow a strict state transition flow:

1. Jobs start in the ``created`` state when instantiated
2. When submitted, they move to ``queued``
3. When execution begins, they transition to ``running``
4. Finally, they reach one of the terminal states:
   * ``completed`` - all tasks finished successfully
   * ``failed`` - one or more tasks failed
   * ``cancelled`` - execution was cancelled

Task States
---------

Each task within a job follows its own state transitions:

* created (initial state)
* staging
* pending
* running
* completed
* failed
* cancelled

Monitoring Jobs
-------------

.. code-block:: python

    async def monitor_job(executor, job):
        while True:
            status = await executor.get_job_status(job)
            print(f"Job state: {status['state']}")
            if status["state"] in ["COMPLETED", "FAILED", "CANCELLED"]:  # Terminal states
                break
            await asyncio.sleep(1)

        # Check final status
        if status["state"] == "COMPLETED":
            print("Job completed successfully")
        elif status["state"] == "FAILED":
            print(f"Job failed: {status.get('error')}")
        else:  # CANCELLED
            print("Job was cancelled")

Error Handling
------------

Handle job execution errors:

.. code-block:: python

    try:
        await executor.submit_job(job)
    except Exception as e:
        print(f"Job submission failed: {e}")

Best Practices
------------

1. Always monitor job status
2. Implement proper error handling
3. Clean up resources after job completion
4. Use appropriate timeouts
5. Log important events and state changes 