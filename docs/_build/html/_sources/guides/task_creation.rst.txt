Task Creation
=============

This guide explains how to create and configure tasks in BenchPRO.

Task Basics
---------

A task represents a single unit of work to be executed. It consists of:

* A name
* A working directory
* A template script
* Resource requirements
* Environment variables

Creating a Task
-------------

Basic Task Creation
~~~~~~~~~~~~~~~~

.. code-block:: python

    from benchpro.core.domain import Task
    from pathlib import Path

    task = Task(
        name="example_task",
        working_dir=Path("/path/to/work"),
        template_path=Path("/path/to/script.sh"),
        variables={"cores": 4, "memory": "8G"}
    )

Template Scripts
-------------

Template scripts are shell scripts that define the actual work:

.. code-block:: bash

    #!/bin/bash
    # example_script.sh
    
    # Use variables passed from the task
    echo "Using ${cores} cores and ${memory} memory"
    
    # Do some work
    sleep 10
    echo "Task completed"

Resource Requirements
------------------

Specify resource requirements through variables:

.. code-block:: python

    task = Task(
        name="resource_intensive_task",
        working_dir=Path("/path/to/work"),
        template_path=Path("/path/to/script.sh"),
        variables={
            "cores": 8,
            "memory": "16G",
            "walltime": 3600,
            "gpu": True
        }
    )

Environment Variables
------------------

Add environment variables to the task:

.. code-block:: python

    task = Task(
        name="env_task",
        working_dir=Path("/path/to/work"),
        template_path=Path("/path/to/script.sh"),
        variables={
            "cores": 4,
            "memory": "8G",
            "ENV": {
                "PATH": "/custom/path:$PATH",
                "LD_LIBRARY_PATH": "/custom/lib:$LD_LIBRARY_PATH"
            }
        }
    )

Task Validation
-------------

Tasks are automatically validated:

* Working directory must exist
* Template script must exist and be executable
* Variables must be valid types
* Resource requirements must be valid

Error Handling
------------

Handle task creation errors:

.. code-block:: python

    from benchpro.core.validation import ValidationError

    try:
        task = Task(
            name="invalid_task",
            working_dir=Path("/nonexistent"),
            template_path=Path("/also/nonexistent"),
            variables={"invalid": object()}
        )
    except ValidationError as e:
        print(f"Task validation failed: {e}")

Best Practices
------------

1. Use Clear Names
~~~~~~~~~~~~~~~

Choose descriptive task names:

.. code-block:: python

    task = Task(
        name="data_preprocessing_step1",
        # ...
    )

2. Organize Working Directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a clear directory structure:

.. code-block:: python

    base_dir = Path("/path/to/project")
    task = Task(
        name="analysis",
        working_dir=base_dir / "analysis" / "step1",
        # ...
    )

3. Template Organization
~~~~~~~~~~~~~~~~~~~~

Keep templates organized and documented:

.. code-block:: python

    templates_dir = Path("/path/to/templates")
    task = Task(
        name="analysis",
        template_path=templates_dir / "analysis" / "process_data.sh",
        # ...
    )

4. Resource Estimation
~~~~~~~~~~~~~~~~~~

Be conservative with resource estimates:

.. code-block:: python

    task = Task(
        name="analysis",
        variables={
            "cores": 4,  # Start with fewer cores
            "memory": "8G",  # Request reasonable memory
            "walltime": 7200,  # Add buffer to time estimate
        }
        # ...
    ) 