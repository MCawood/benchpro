import asyncio
import subprocess
import uuid
from typing import List, Optional
from benchpro.core.domain import Task, TaskStatus, Job
from benchpro.core.scheduler import SchedulerBackend, SlurmBackend, LocalBackend
from benchpro.core.results import ResultStore
from benchpro.core.config import Config

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

    async def run_tasks(self, tasks: List[Task], suite_id: str = "unknown"):
        """Run a list of tasks."""
        # Create a run ID
        run_id = str(uuid.uuid4())
        self.result_store.save_run(run_id, suite_id, system=self.backend_type)
        print(f"Started run {run_id}")

        if self.backend_type == "local":
            futures = [self._run_local_task(task, run_id) for task in tasks]
            await asyncio.gather(*futures)
        elif self.backend_type == "slurm":
            for task in tasks:
                self._submit_slurm_task(task, run_id)

    async def _run_local_task(self, task: Task, run_id: str):
        # Save initial state
        self.result_store.save_task(task, run_id)
        
        async with self.semaphore:
            task.status = TaskStatus.RUNNING
            self.result_store.save_task(task, run_id)
            print(f"Starting task {task.task_id}")
            
            try:
                # Start timing
                import time
                start_time = time.time()
                
                proc = await asyncio.create_subprocess_shell(
                    task.command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                duration = (time.time() - start_time) * 1000
                task.duration_ms = duration
                task.exit_code = proc.returncode
                
                if proc.returncode == 0:
                    task.status = TaskStatus.COMPLETED
                    print(f"Output for {task.task_id}:")
                    print(stdout.decode())
                else:
                    task.status = TaskStatus.FAILED
                    print(f"Error for {task.task_id}:")
                    print(stderr.decode())
                    
                print(f"Finished task {task.task_id} with code {task.exit_code}")
                
            except Exception as e:
                print(f"Task {task.task_id} failed with exception: {e}")
                task.status = TaskStatus.FAILED
            
            # Save final state
            self.result_store.save_task(task, run_id)

    def _submit_slurm_task(self, task: Task, run_id: str):
        # Save initial state
        self.result_store.save_task(task, run_id)
        
        # Create a simple job script
        # Create a simple job script
        sb_lines = [
            "#!/bin/bash",
            f"#SBATCH --job-name={task.task_id}",
            f"#SBATCH --nodes={task.resources.nodes}",
            f"#SBATCH --ntasks-per-node={task.resources.ranks_per_node}",
            f"#SBATCH --cpus-per-task={task.resources.threads}"
        ]
        
        if task.resources.time:
            sb_lines.append(f"#SBATCH --time={task.resources.time}")
        if task.resources.partition:
            sb_lines.append(f"#SBATCH --partition={task.resources.partition}")
        elif self.config and self.config.system.partition:
            sb_lines.append(f"#SBATCH --partition={self.config.system.partition}")

        if task.resources.account:
            sb_lines.append(f"#SBATCH --account={task.resources.account}")
        elif self.config and self.config.system.account:
            sb_lines.append(f"#SBATCH --account={self.config.system.account}")
        if task.resources.qos:
            sb_lines.append(f"#SBATCH --qos={task.resources.qos}")
        if task.resources.gpus > 0:
            sb_lines.append(f"#SBATCH --gpus-per-node={task.resources.gpus}")
            
        sb_lines.append("")
        sb_lines.append(task.command)
        
        script = "\n".join(sb_lines)
        job = Job(
            job_id=f"job_{task.task_id}",
            tasks=[task.task_id],
            script_content=script
        )
        
        try:
            scheduler_id = self.scheduler.submit_job(job)
            task.job_id = scheduler_id
            task.status = TaskStatus.RUNNING # Or SUBMITTED
            print(f"Submitted task {task.task_id} as job {scheduler_id}")
        except Exception as e:
            print(f"Failed to submit task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            
        # Save updated state
        self.result_store.save_task(task, run_id)
