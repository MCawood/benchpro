# BenchPro 2.0: Architecture Review Briefing

## 1. Executive Summary
BenchPro 2.0 is a deterministic benchmark orchestrator for HPC systems. We are proposing a significant architectural refactor to support complex workflows (multi-stage dependent jobs) and high-throughput job packing. This document outlines the current state, its limitations, and our proposed "JobBuilder" pattern. We seek a critical review of this design before implementation.

## 2. Current Architecture (The "Before" State)
The current flow is linear and assumes a 1-to-1 mapping between a logical **Benchmark** and a physical **Job**.

### Logic Flow
1.  **User Input**: A Suite YAML file defining a matrix of parameters (e.g., node counts, input sizes).
2.  **Planner**: Expands this matrix into a list of `Benchmark` objects.
    *   *Constraint*: A `Benchmark` contains a list of `Tasks`.
    *   *Constraint*: The `Planner` assumes all Tasks in a Benchmark share the same resource requirements (Nodes, Partition, etc.).
3.  **Executor**: Iterates through the list of `Benchmarks`.
    *   For each Benchmark, it generates **one** submission script (Slurm script).
    *   It submits this script as **one** Job.

### The Limitation
This architecture fails in two critical high-value scenarios:

*   **Scenario A: Resource Inefficiency in Multi-Stage Workflows**:
    If a user simply defines a benchmark with a "Mesh" task (1 node) and a "Solve" task (128 nodes), the current Executor generates a single Job. This job must request 128 nodes to satisfy the Solver, meaning the Meshing step wastes 127 nodes while it runs. The system lacks the ability to **split** a logical Benchmark into specific physical Jobs with dependencies.

*   **Scenario B: Queue Overhead in High-Throughput**:
    If a user runs 100 small benchmarks (1 node each), the Executor submits 100 separate Jobs. This floods the scheduler queue. The system lacks the ability to **pack** independent Benchmarks into a single physical Job.

## 3. Proposed Architecture (The "After" State)
We propose decoupling the **Logical Definition** of work from the **Physical Execution** of work by introducing a middle layer: the **JobBuilder**.

### New Logic Flow
1.  **Planner**: Generates `Benchmarks` containing `Tasks`.
    *   *Change*: `Tasks` now explicitly hold their own `ResourceRequest` (Nodes, Time, etc.), inheriting from the Benchmark but allowing overrides.
    *   *Change*: `Tasks` define their logic dependencies (e.g., `Task B` depends on `Task A`).

2.  **JobBuilder (The New Component)**:
    *   **Input**: A list of `Benchmarks` (Logic).
    *   **Process**: Groups `Tasks` into `Jobs` based on a **Strategy**.
    *   **Output**: A list (or DAG) of `Job` objects (Physical).

3.  **Executor**:
    *   **Input**: A list/DAG of `Jobs`.
    *   **Process**: Submits Jobs to the scheduler, respecting Job-level dependencies.

### Strategies
The `JobBuilder` enables flexible mapping strategies:
*   **Default (1:1)**: Maps 1 Benchmark to 1 Job (Preserves current behavior for simple cases).
*   **Split (Variance Detection)**: If Tasks within a Benchmark have differing resources, it splits them into separate dependent Jobs (Solves Scenario A).
*   **Pack (Optimization)**: Groups independent Tasks with identical resources into shared Jobs (Solves Scenario B).

## 4. Implementation Details

### Domain Model Changes
**Task Object**:
```python
class Task(BaseModel):
    task_id: str
    resources: ResourceRequest  # Authoritative resources for this specific step
    dependencies: List[str]     # IDs of logic dependencies (other tasks)
    parameters: Dict[str, Any]  # Input variables (e.g. input_file="large.in")
    # ...
```

**Job Object**:
```python
class Job(BaseModel):
    job_id: str
    resources: ResourceRequest  # Aggregated/Max resources for the implementation
    tasks: List[Task]           # The tasks to run in this script
    job_dependencies: List[str] # Scheduler dependencies (e.g., afterok:12345)
```

### Parameter Handling
Input parameters (variables defined in the generic matrix) are resolved at the **Planner** level.
*   If a parameter affects the command line (e.g., `-i input.dat`), it is baked into `Task.command`.
*   If a parameter affects resources (e.g., `nodes: 128`), it is baked into `Task.resources`.
*   The `JobBuilder` **does not** need to re-evaluate parameters; it operates purely on the concrete `ResourceRequest` of inputs.

## 5. Example Scenarios

### Scenario A: The "Big Simulation" (Multi-Stage)
*User wants: Mesh (1 node) -> Decomp (1 node) -> Solve (128 nodes)*

1.  **Planner**: Produces 1 Benchmark with 3 Tasks.
    *   Task 1 (Mesh): Nodes=1
    *   Task 2 (Decomp): Nodes=1
    *   Task 3 (Solve): Nodes=128
2.  **JobBuilder (Split Strategy)**:
    *   Detects Resource Variance.
    *   Creates **Job A** (1 Node): Runs Task 1 & 2.
    *   Creates **Job B** (128 Nodes): Runs Task 3.
    *   Sets `Job B` dependency on `Job A`.
3.  **Executor**: Submits Job A, gets ID `101`. Submits Job B with `-d afterok:101`.

### Scenario B: The "Parameter Sweep" (Throughput)
*User wants: Run 'APP' with inputs X, Y, Z on 1 node each.*

1.  **Planner**: Produces 3 Benchmarks (one for each input).
    *   Bench 1: Nodes=1
    *   Bench 2: Nodes=1
    *   Bench 3: Nodes=1
2.  **JobBuilder (Pack Strategy)**:
    *   Detects identical signatures.
    *   Creates **Job A** (1 Node).
    *   Script: `srun task1 & srun task2 & srun task3 & wait` (or equivalent sequential command).
3.  **Executor**: Submits 1 Job.

## 6. Request for Feedback

We specifically request feedback on:
1.  **Complexity vs Value**: Is the `JobBuilder` abstraction too complex for a standard benchmark tool, or is it a necessary evolution for HPC workflows?
2.  **Job Dependency Complexity**: How should we handle failure in a chain? (e.g., If Mesh fails, should Solves be cancelled automatically by the scheduler, or do we need logical handling?)
3.  **Opaque Packing**: Is "automagical" packing dangerous? Should users have explicit control over how tasks are packed (e.g., `--pack-size=10`)?
