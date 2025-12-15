from typing import List, Protocol, Dict, Optional, Tuple, Set, Iterable
from collections import defaultdict
from benchpro.core.domain import Benchmark, Job, Task, ResourceRequest

class JobBuilderStrategy(Protocol):
    name: str
    
    def build_jobs(self, benchmarks: Iterable[Benchmark]) -> List[Job]:
        """Convert a list of benchmarks into a list of executable Jobs."""
        ...

class OneToOneStrategy:
    """
    Default Strategy: 1 Benchmark -> 1 Job.
    Assumes all tasks in the benchmark are compatible.
    """
    name = "one_to_one"

    def build_jobs(self, benchmarks: Iterable[Benchmark]) -> List[Job]:
        jobs = []
        for bench in benchmarks:
            # Create one Job per Benchmark
            # Create one Job per Benchmark
            # We use the Benchmark's ID as the base for the Job ID
            job_id = bench.benchmark_id
            
            # Aggregate tasks
            tasks = bench.tasks
            
            # Determine resources (Naive: use the first task's resources or benchmark default)
            # In V1 Design, we assume consistency.
            if not tasks:
                continue
                
            # Use the first task's resources as the Job's resources
            # This is the "OneToOne" assumption: no variance.
            resources = tasks[0].resources
            
            # Sequential execution plan by default
            execution_plan = [("sequential", t.task_id) for t in tasks]
            
            # Aggregate external dependencies
            ext_deps = set()
            for t in tasks:
                ext_deps.update(t.scheduler_dependencies)

            job = Job(
                job_id=job_id,
                scheduler=resources.scheduler,
                tasks=tasks,
                resources=resources,
                execution_plan=execution_plan,
                scheduler_dependencies=sorted(list(ext_deps))
            )
            jobs.append(job)
            
        # Map logical dependencies to job dependencies
        self._resolve_job_dependencies(jobs)
        return sorted(jobs, key=lambda j: j.job_id)

    def _resolve_job_dependencies(self, jobs: List[Job]):
        """
        If Task A depends on Task B, and Task A is in Job A and Task B is in Job B,
        then Job A depends on Job B.
        """
        task_to_job = {}
        for job in jobs:
            for task in job.tasks:
                task_to_job[task.task_id] = job.job_id
                
        for job in jobs:
            deps = set()
            for task in job.tasks:
                for dep_id in task.dependencies:
                    if dep_id in task_to_job:
                        dep_job_id = task_to_job[dep_id]
                        if dep_job_id != job.job_id:
                            deps.add(dep_job_id)
            job.job_dependencies = sorted(list(deps))


class SplitByVarianceStrategy:
    """
    Splits a Benchmark into multiple Jobs if tasks have differing resource signatures.
    """
    name = "split_by_variance"

    def build_jobs(self, benchmarks: Iterable[Benchmark]) -> List[Job]:
        jobs = []
        
        for bench in benchmarks:
            # Group tasks by signature
            groups = defaultdict(list)
            for task in bench.tasks:
                sig = task.resources.signature_for_packing()
                groups[sig].append(task)
            
            # Create a Job for each group
            # We need to maintain some order, but groups dict is unordered. 
            # We should probably process tasks in order and grouped contiguous blocks?
            # But the user might define Mesh (1) -> Decomp (1) -> Solve (128).
            # The signature group (1) matches Mesh and Decomp. Ideally they go in same job.
            
            # Logic: Iterate tasks, detecting signature changes? 
            # Or just blindly group all tasks with signature X into Job X?
            # Using blind grouping allows non-contiguous tasks to share a job (if that makes sense).
            # But for sequential execution, that reorders tasks!
            # For correctness, we must preserve order for sequential execution?
            # Actually, tasks in a Benchmark are usually ordered.
            
            # Let's do: Contiguous blocks of same signature.
            current_sig = None
            current_block = []
            
            for task in bench.tasks:
                sig = task.resources.signature_for_packing()
                if sig != current_sig:
                    if current_block:
                        self._flush_block(jobs, bench, current_block, current_sig)
                    current_sig = sig
                    current_block = [task]
                else:
                    current_block.append(task)
            
            if current_block:
                self._flush_block(jobs, bench, current_block, current_sig)
                
        self._resolve_job_dependencies(jobs)
        return sorted(jobs, key=lambda j: j.job_id)

    def _flush_block(self, jobs, bench, tasks, sig):
        # Create a unique job ID for this block
        # Use simple suffix numbering
        base_id = bench.benchmark_id
        idx = len([j for j in jobs if j.job_id.startswith(f"{base_id}_") or j.job_id == base_id])
        job_id = f"{base_id}_{idx}"
        
        resources = tasks[0].resources
        execution_plan = [("sequential", t.task_id) for t in tasks]
        
        # Aggregate external dependencies
        ext_deps = set()
        for t in tasks:
            ext_deps.update(t.scheduler_dependencies)

        job = Job(
            job_id=job_id,
            scheduler=resources.scheduler,
            tasks=tasks,
            resources=resources,
            execution_plan=execution_plan,
            scheduler_dependencies=sorted(list(ext_deps))
        )
        jobs.append(job)

    def _resolve_job_dependencies(self, jobs: List[Job]):
        # Same dependency resolution logic
        # Could be shared in a base class or utility
        task_to_job = {}
        for job in jobs:
            for task in job.tasks:
                task_to_job[task.task_id] = job.job_id
                
        for job in jobs:
            deps = set()
            for task in job.tasks:
                for dep_id in task.dependencies:
                    if dep_id in task_to_job:
                        dep_job_id = task_to_job[dep_id]
                        if dep_job_id != job.job_id:
                            deps.add(dep_job_id)
            job.job_dependencies = sorted(list(deps))


class JobBuilder:
    def __init__(self, strategy_name: str = "one_to_one"):
        self.strategies = {
            "one_to_one": OneToOneStrategy(),
            "split_by_variance": SplitByVarianceStrategy(),
            # "pack": PackBySignatureStrategy() # Future
        }
        self.strategy = self.strategies.get(strategy_name, OneToOneStrategy())
    
    def build(self, benchmarks: List[Benchmark]) -> List[Job]:
        return self.strategy.build_jobs(benchmarks)
