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
            if status["state"] in ["completed", "failed", "cancelled"]:
                break
            await asyncio.sleep(1)

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