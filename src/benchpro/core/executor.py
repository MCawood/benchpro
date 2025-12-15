import asyncio
import subprocess
import uuid
from typing import List, Optional
from benchpro.core.domain import Task, TaskStatus, Job
from benchpro.core.scheduler import SchedulerBackend, SlurmBackend, LocalBackend
from benchpro.core.results import ResultStore
from benchpro.core.config import Config
from benchpro.core.logger import get_logger
from benchpro.core.exceptions import TaskError

logger = get_logger()

class Executor:
    def __init__(self, backend: str = "local", max_concurrent: int = 4, result_store: ResultStore = None, config: Config = None):
        self.backend_type = backend
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.result_store = result_store or ResultStore()
        self.config = config
        
        if backend == "slurm":
            self.scheduler = SlurmBackend()
        else:
            self.scheduler = LocalBackend()

    async def run_benchmarks(self, benchmarks: List["Benchmark"], suite_id: str = "unknown", strategy: str = "one_to_one"):
        """Run a list of benchmarks using the JobBuilder strategy."""
        from benchpro.core.services.job_builder import JobBuilder
        
        # Create a run ID
        # Format: {suite}-{short_uuid} (e.g. lammps-a1b2c3d4)
        short_hash = str(uuid.uuid4().hex)[:8]
        run_id = f"{suite_id}-{short_hash}"
        
        self.result_store.save_run(run_id, suite_id, system=self.backend_type)
        logger.info(f"Started run {run_id}")

        # Build Jobs
        builder = JobBuilder(strategy)
        jobs = builder.build(benchmarks)
        label = "benchmarks"
        if suite_id == "build_process":
            label = "applications"
        logger.info(f"Generated {len(jobs)} jobs from {len(benchmarks)} {label}")

        if self.backend_type == "local":
            # Flatten execution: Run each job's tasks
            # For local, we ignore job grouping for now and just run tasks to keep it simple,
            # unless we implement a LocalJobExecutor.
            # But wait, logic dependencies might matter.
            # Ideally we should execute Jobs sequentially if they depend on each other.
            # Since jobs are topological sorted by JobBuilder (usually), sequential iteration works.
            
            # Helper to extract tasks in order
            all_tasks = []
            for job in jobs:
                all_tasks.extend(job.tasks)
                
            futures = [self._run_local_task(task, run_id) for task in all_tasks]
            await asyncio.gather(*futures)
            
        elif self.backend_type == "slurm":
            self._submit_slurm_jobs(jobs, run_id)

    def _submit_slurm_jobs(self, jobs: List[Job], run_id: str):
        """Submit jobs to Slurm, respecting dependencies."""
        job_id_map = {} # Internal Job ID -> Scheduler Job ID
        
        for job in jobs:
            # Check dependencies
            dependency_ids = []
            for dep_job_id in job.job_dependencies:
                if dep_job_id in job_id_map:
                    dependency_ids.append(str(job_id_map[dep_job_id]))
                else:
                    logger.warning(f"Dependency {dep_job_id} for job {job.job_id} not found/submitted yet")
            
            # External dependencies (e.g. build jobs)
            if job.scheduler_dependencies:
                 dependency_ids.extend(job.scheduler_dependencies)
            
            # Submit
            try:
                scheduler_id = self._submit_job(job, run_id, dependency_ids)
                if scheduler_id:
                    job_id_map[job.job_id] = scheduler_id
            except Exception as e:
                logger.error(f"Failed to submit job {job.job_id}: {e}")
                # We stop submission? Or just continue?
                # Per design, downstream jobs will be skipped if we were strict,
                # but currently we just log. Downstream jobs might fail at submission if deps missing.

    def _submit_job(self, job: Job, run_id: str, dependency_ids: List[str] = None) -> Optional[str]:
        """Submit a single Job object to Slurm."""
        # 1. Prepare tasks (paths, result store)
        import os
        import os
        from pathlib import Path
        
        first_task = job.tasks[0]
        
        # Determine working directory
        if first_task.working_directory:
            working_directory = first_task.working_directory
        else:
            # Create isolated workspace for this job/run
            # Use configured workspace dir or default
            # Structure: {workspace_root}/workspaces/runs/{run_id}
            
            ws_root = Path.cwd() / "benchpro"
            if self.config and self.config.system.workspace_dir:
                ws_root = Path(self.config.system.workspace_dir)
            
            # Use 'workspaces/runs' subdir
            runs_root = ws_root / "workspaces" / "runs"
            
            working_directory = str(runs_root / run_id)
            
            # Create it
            Path(working_directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created workspace for job {job.job_id}: {working_directory}")
        
        for task in job.tasks:
            if not task.working_directory:
                task.working_directory = working_directory
            
            # Output files
            task.output_file = os.path.join(task.working_directory, f"{task.task_id}.out")
            task.error_file = os.path.join(task.working_directory, f"{task.task_id}.err")
            self.result_store.save_task(task, run_id)

        # 2. Generate Script
        # Simple generation for now, ignoring template complexity of Benchmark
        script = self._generate_slurm_script(job, first_task, dependency_ids)
        
        # 3. Write Script
        script_file = os.path.join(working_directory, f"{job.job_id}.sh")
        with open(script_file, "w") as f:
            f.write(script)
            
        # 4. Update Tasks
        for task in job.tasks:
            task.script_file = script_file
            self.result_store.save_task(task, run_id)
            
        job.script_content = script
        
        # 5. Submit
        try:
            scheduler_id = self.scheduler.submit_job(job)
            job.scheduler_job_id = scheduler_id
            job.status = "submitted"
            
            # Update tasks
            for task in job.tasks:
                task.job_id = scheduler_id
                task.status = TaskStatus.RUNNING # SUBMITTED/QUEUED really
                self.result_store.save_task(task, run_id)
                
            logger.info(f"Submitted job {job.job_id} as {scheduler_id}")
            return scheduler_id
        except Exception as e:
            logger.error(f"Submission failed: {e}")
            for task in job.tasks:
                task.status = TaskStatus.FAILED
                task.exit_code = 1
                self.result_store.save_task(task, run_id)
            return None

    def _generate_slurm_script(self, job: Job, context_task: Task, dependency_ids: List[str] = None) -> str:
        res = job.resources
        sb_lines = [
            "#!/bin/bash",
            f"#SBATCH --job-name={job.job_id}",
            f"#SBATCH --nodes={res.nodes}",
            f"#SBATCH --ntasks-per-node={res.ranks_per_node}",
            f"#SBATCH --cpus-per-task={res.threads}",
            f"#SBATCH --output={context_task.working_directory}/{job.job_id}.out",
            f"#SBATCH --error={context_task.working_directory}/{job.job_id}.err"
        ]
        
        if res.time:
            sb_lines.append(f"#SBATCH --time={res.time}")
            
        # Config overrides
        partition = res.partition or (self.config.system.partition if self.config else None)
        account = res.account or (self.config.system.account if self.config else None)
        reservation = res.reservation or (self.config.system.reservation if self.config else None)
        
        if partition:
            sb_lines.append(f"#SBATCH --partition={partition}")
        if reservation:
            sb_lines.append(f"#SBATCH --reservation={reservation}")
        if account:
            sb_lines.append(f"#SBATCH --account={account}")
        else:
            # Strict validation for account
            raise TaskError("Slurm account not specified. Please set 'system.account' in your config or in benchmark resources.")
            
        if partition:
            sb_lines.append(f"#SBATCH --partition={partition}")
        if res.gpus > 0:
            sb_lines.append(f"#SBATCH --gpus-per-node={res.gpus}")
            
        if dependency_ids:
            deps = ":".join(dependency_ids)
            sb_lines.append(f"#SBATCH --dependency=afterok:{deps}")
            
        sb_lines.append("")
        sb_lines.append("export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK")
        sb_lines.append("")
        
        # Execution Plan
        # Default: Sequential
        for task in job.tasks:
            sb_lines.append(f"echo 'Starting task {task.task_id}'")
            sb_lines.append(task.command)
            sb_lines.append("")
            
        return "\n".join(sb_lines)

    def _parse_walltime(self, time_str: str) -> int:
        """Parse walltime string (HH:MM:SS or MM:SS or S) to seconds."""
        if not time_str:
            return 3600
        
        try:
            # If plain integer
            if str(time_str).isdigit():
                return int(time_str)
                
            parts = time_str.split(':')
            if len(parts) == 3: # HH:MM:SS
                h, m, s = map(int, parts)
                return h * 3600 + m * 60 + s
            elif len(parts) == 2: # MM:SS
                m, s = map(int, parts)
                return m * 60 + s
            elif len(parts) == 1:
                return int(parts[0])
            else:
                logger.warning(f"Could not parse time '{time_str}', using default 3600s")
                return 3600
        except ValueError:
            logger.warning(f"Could not parse time '{time_str}', using default 3600s")
            return 3600
            
    async def _run_local_task(self, task: Task, run_id: str):
        # ... (Same as before, simplified for brevity in this replace call, but I need to keep the content)
        # Just calling out that I'm keeping the method.
        # Wait, the replace tool replaces the block. I need to output the FULL CONTENT of _run_local_task if I'm replacing the whole class.
        # I only replaced up to the end of _submit_slurm_benchmark.
        # So I need to verify I didn't delete _run_local_task logic.
        # I will include `_run_local_task` implementation in the replacement content to be safe.
        
        # Save initial state
        # Save initial state
        if not task.working_directory:
            import os
            from pathlib import Path
            
            # Create isolated workspace for local task too
            ws_root = Path.cwd() / "benchpro"
            if self.config and self.config.system.workspace_dir:
                ws_root = Path(self.config.system.workspace_dir)
                
            runs_root = ws_root / "workspaces" / "runs"
            task.working_directory = str(runs_root / run_id)
            Path(task.working_directory).mkdir(parents=True, exist_ok=True)
            
        # Set output/error files
        import os
        task.output_file = os.path.join(task.working_directory, f"{task.task_id}.out")
        task.error_file = os.path.join(task.working_directory, f"{task.task_id}.err")
        
        self.result_store.save_task(task, run_id)
        
        async with self.semaphore:
            task.status = TaskStatus.RUNNING
            self.result_store.save_task(task, run_id)
            logger.info(f"Starting task {task.task_id}")
            
            try:
                import time
                start_time = time.time()
                timeout = 3600 
                if task.resources.time:
                    timeout = self._parse_walltime(task.resources.time)
                elif self.config and self.config.system.default_walltime:
                    timeout = self.config.system.default_walltime
                
                with open(task.output_file, "w") as out_f, open(task.error_file, "w") as err_f:
                    proc = await asyncio.create_subprocess_exec(
                        'bash', '-l', '-c', task.command,
                        stdout=out_f,
                        stderr=err_f
                    )
                    
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=timeout)
                    except asyncio.TimeoutError:
                        logger.error(f"Task {task.task_id} timed out after {timeout}s")
                        proc.terminate()
                        try:
                            await asyncio.wait_for(proc.wait(), timeout=5)
                        except asyncio.TimeoutError:
                            proc.kill()
                        task.status = TaskStatus.FAILED
                        with open(task.error_file, "a") as f:
                            f.write(f"\\n[BENCHPRO] Task timed out after {timeout}s\\n")
                        raise TimeoutError(f"Task exceeded walltime of {timeout}s")

                duration = (time.time() - start_time) * 1000
                task.duration_ms = duration
                task.exit_code = proc.returncode
                
                if proc.returncode == 0:
                    task.status = TaskStatus.COMPLETED
                else:
                    task.status = TaskStatus.FAILED
                    logger.error(f"Task {task.task_id} failed with code {proc.returncode}")
                
            except Exception as e:
                logger.error(f"Task {task.task_id} failed with exception: {e}")
                task.status = TaskStatus.FAILED
                task.exit_code = -1
            
            self.result_store.save_task(task, run_id)
