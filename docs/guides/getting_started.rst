Getting Started
===============

This guide will help you get started with BenchPRO.

Installation
-----------

Install BenchPRO using pip:

.. code-block:: bash

    pip install benchpro

Or install from source:

.. code-block:: bash

    git clone https://github.com/yourusername/benchpro.git
    cd benchpro
    pip install -e .

Requirements
----------

BenchPRO requires:

* Python 3.12 or later
* psutil
* asyncio

Basic Configuration
----------------

Create a basic configuration file:

.. code-block:: python

    # config.py
    from pathlib import Path

    WORKING_DIR = Path("/path/to/workdir")
    DEFAULT_RESOURCES = {
        "cores": 4,
        "memory": "8G",
        "walltime": 3600,
    }

First Steps
---------

1. Create a Task
~~~~~~~~~~~~~~

.. code-block:: python

    from benchpro.core.domain import Task
    from pathlib import Path

    task = Task(
        name="example_task",
        working_dir=Path("/path/to/work"),
        template_path=Path("/path/to/script.sh"),
        variables={"cores": 4, "memory": "8G"}
    )

2. Create a Job
~~~~~~~~~~~~~

.. code-block:: python

    from benchpro.core.domain import Job, JobResources

    job = Job(
        name="example_job",
        working_dir=Path("/path/to/job"),
        tasks=[task],
        resources=JobResources(cores=4, memory="8G")
    )

3. Execute the Job
~~~~~~~~~~~~~~~

.. code-block:: python

    from benchpro.core.infrastructure import LocalExecutor
    import asyncio

    async def run_job():
        executor = LocalExecutor()
        await executor.submit_job(job)
        
        # Monitor status
        while True:
            status = await executor.get_job_status(job)
            if status["state"] in ["completed", "failed", "cancelled"]:
                break
            await asyncio.sleep(1)

    asyncio.run(run_job())

Next Steps
---------

* Learn about :doc:`task_creation`
* Understand :doc:`job_execution`
* Explore :doc:`resource_management`
* Read the :doc:`../architecture/index` 