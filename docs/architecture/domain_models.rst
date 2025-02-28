Domain Models
============

The domain models form the core of BenchPRO's business logic. They encapsulate the essential concepts and rules of the system.

Task Model
---------

The Task model represents a single unit of work to be executed. It manages its own state and validation rules.

.. code-block:: python

    class Task:
        name: str
        working_dir: Path
        template_path: Path
        variables: Dict[str, Any]
        state: TaskState
        error: Optional[str]

Key Features:
~~~~~~~~~~~~

* **State Management**: Tasks transition through various states (PENDING → RUNNING → COMPLETED/FAILED)
* **Resource Requirements**: Tasks specify their resource needs (CPU, memory)
* **Error Handling**: Comprehensive error tracking and reporting
* **Validation**: Built-in validation for paths and variables

Job Model
--------

The Job model represents a collection of tasks that should be executed together. It manages resource allocation and overall execution state.

.. code-block:: python

    class Job:
        name: str
        working_dir: Path
        tasks: List[Task]
        resources: JobResources
        state: JobState
        error: Optional[str]

Key Features:
~~~~~~~~~~~

* **Resource Management**: Tracks and validates resource requirements
* **Task Coordination**: Manages multiple tasks as a single unit
* **State Propagation**: Job state reflects the collective state of its tasks
* **Error Aggregation**: Collects and reports errors from all tasks

State Management
--------------

Both Task and Job models use state enums to track their execution status:

Task States:
~~~~~~~~~~

* **CREATED**: Initial state when task is instantiated
* **STAGING**: Task is preparing for execution
* **PENDING**: Task is ready for execution
* **RUNNING**: Currently executing
* **COMPLETED**: Successfully finished
* **FAILED**: Execution failed
* **CANCELLED**: Execution was cancelled

Job States:
~~~~~~~~~

* **CREATED**: Initial state when job is instantiated
* **QUEUED**: Job is queued for execution
* **RUNNING**: Currently executing tasks sequentially
* **COMPLETED**: All tasks completed successfully
* **FAILED**: One or more tasks failed
* **CANCELLED**: Execution was cancelled

State Transitions:
~~~~~~~~~~~~~~~

Valid transitions between states are strictly controlled:

Task Transitions:
^^^^^^^^^^^^^^^

* CREATED → STAGING/PENDING/FAILED/CANCELLED
* STAGING → PENDING/FAILED/CANCELLED
* PENDING → RUNNING/FAILED/CANCELLED
* RUNNING → COMPLETED/FAILED/CANCELLED
* COMPLETED/FAILED/CANCELLED: Terminal states

Job Transitions:
^^^^^^^^^^^^^

* CREATED → QUEUED/CANCELLED
* QUEUED → RUNNING/CANCELLED
* RUNNING → COMPLETED/FAILED/CANCELLED
* COMPLETED/FAILED/CANCELLED: Terminal states

Resource Management
----------------

Resources are tracked using the JobResources model:

.. code-block:: python

    class JobResources:
        cores: int
        memory: str  # e.g., "8G"
        nodes: int = 1
        walltime: int = 3600  # seconds

Features:
~~~~~~~~

* **Memory Parsing**: Handles human-readable memory strings (e.g., "8G", "512M")
* **Validation**: Ensures resource requests are valid
* **Scaling**: Supports both single-node and multi-node execution
* **Time Limits**: Enforces execution time constraints

Usage Example
-----------

Here's a basic example of creating and using these models:

.. code-block:: python

    # Create a task
    task = Task(
        name="example_task",
        working_dir=Path("/path/to/work"),
        template_path=Path("/path/to/script.sh"),
        variables={"cores": 4, "memory": "8G"}
    )

    # Create a job with the task
    job = Job(
        name="example_job",
        working_dir=Path("/path/to/job"),
        tasks=[task],
        resources=JobResources(cores=4, memory="8G")
    )

    # Task and job states are automatically managed
    assert job.state == JobState.CREATED  # Initial state
    assert task.state == TaskState.CREATED  # Initial state

    # State transitions are validated
    job.transition_to(JobState.QUEUED)  # Valid transition
    task.transition_to(TaskState.STAGING)  # Valid transition 