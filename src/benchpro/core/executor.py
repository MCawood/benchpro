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

    async def run_benchmarks(self, benchmarks: List["Benchmark"], suite_id: str = "unknown"):
        """Run a list of benchmarks."""
        # Create a run ID
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_hash = str(uuid.uuid4())[:6]
        
        # Determine node count from first benchmark/task
        node_count = "0"
        if benchmarks and benchmarks[0].tasks:
            node_count = str(benchmarks[0].tasks[0].resources.nodes)
            
        run_id = f"{suite_id}_{node_count}_{timestamp}_{short_hash}"
        
        self.result_store.save_run(run_id, suite_id, system=self.backend_type)
        logger.info(f"Started run {run_id}")

        if self.backend_type == "local":
            # For local, we still run tasks individually for now, or we could run benchmarks sequentially
            # Let's flatten tasks for local execution to keep concurrency simple
            tasks = []
            for b in benchmarks:
                tasks.extend(b.tasks)
                
            futures = [self._run_local_task(task, run_id) for task in tasks]
            await asyncio.gather(*futures)
        elif self.backend_type == "slurm":
            for bench in benchmarks:
                self._submit_slurm_benchmark(bench, run_id)

    async def _run_local_task(self, task: Task, run_id: str):
        # Save initial state
        if not task.working_directory:
            import os
            task.working_directory = os.getcwd()
            
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
                # Start timing
                import time
                start_time = time.time()
                
                # Open output files
                with open(task.output_file, "w") as out_f, open(task.error_file, "w") as err_f:
                    # Run in bash -l to ensure module commands work (Lmod requires login shell)
                    # Use create_subprocess_exec to properly handle command with bash -l -c
                    proc = await asyncio.create_subprocess_exec(
                        'bash', '-l', '-c', task.command,
                        stdout=out_f,
                        stderr=err_f
                    )
                    await proc.wait()
                
                duration = (time.time() - start_time) * 1000
                task.duration_ms = duration
                task.exit_code = proc.returncode
                
                if proc.returncode == 0:
                    task.status = TaskStatus.COMPLETED
                    logger.debug(f"Task {task.task_id} completed")
                else:
                    task.status = TaskStatus.FAILED
                    logger.error(f"Task {task.task_id} failed with code {proc.returncode}")
                    
                logger.info(f"Finished task {task.task_id} with code {task.exit_code}")
                
            except Exception as e:
                logger.error(f"Task {task.task_id} failed with exception: {e}")
                task.status = TaskStatus.FAILED
                # We don't raise here because we want to continue running other tasks
                # But we could collect errors and raise a TaskError at the end if needed
                # For now, just logging is fine as the status is updated
            
            # Save final state
            self.result_store.save_task(task, run_id)

    def _submit_slurm_benchmark(self, bench: "Benchmark", run_id: str):
        # We assume all tasks in a benchmark share the same resources (or we take the max/sum)
        # For now, let's assume 1 task per benchmark or uniform resources
        if not bench.tasks:
            return
            
        first_task = bench.tasks[0]
        
        # Save initial state for all tasks
        import os
        for task in bench.tasks:
            if not task.working_directory:
                task.working_directory = os.getcwd()
            
            # Set expected output/error files based on SBATCH defaults or template
            # If template is used, we rely on what's in the template (usually {{ benchmark_id }}.out)
            # If default generation, we set it explicitly
            if not bench.template:
                task.output_file = os.path.join(task.working_directory, f"{bench.benchmark_id}.out")
                task.error_file = os.path.join(task.working_directory, f"{bench.benchmark_id}.err")
            else:
                # Best guess for template - usually benchmark_id.out
                # We could try to parse it but that's hard
                task.output_file = os.path.join(task.working_directory, f"{bench.benchmark_id}.out")
                task.error_file = os.path.join(task.working_directory, f"{bench.benchmark_id}.err")
            
            self.result_store.save_task(task, run_id)
        
        # Create job script
        if bench.template:
            # Use provided template
            from benchpro.core.templating import TemplateEngine
            
            # Create context for template
            # We aggregate resources from the first task (assuming uniform)
            context = {
                "benchmark_id": bench.benchmark_id,
                "tasks": bench.tasks,
                "nodes": first_task.resources.nodes,
                "ranks_per_node": first_task.resources.ranks_per_node,
                "threads": first_task.resources.threads,
                "gpus": first_task.resources.gpus,
                "time": first_task.resources.time,
                "partition": first_task.resources.partition or (self.config.system.partition if self.config else None),
                "account": first_task.resources.account or (self.config.system.account if self.config else None),
                "qos": first_task.resources.qos,
                "command": first_task.command # For simple templates
            }
            
            # Add task parameters to context (from first task)
            if first_task.parameters:
                context.update(first_task.parameters)
                
            engine = TemplateEngine(context)
            
            # If template is a path, read it
            import os
            if os.path.exists(bench.template):
                with open(bench.template, "r") as f:
                    template_content = f.read()
            else:
                # Assume it's the content itself (unlikely for file path but possible for inline)
                template_content = bench.template
                
            script = engine.render(template_content)
            
        else:
            # Default script generation
            sb_lines = [
                "#!/bin/bash",
                f"#SBATCH --job-name={bench.benchmark_id}",
                f"#SBATCH --nodes={first_task.resources.nodes}",
                f"#SBATCH --ntasks-per-node={first_task.resources.ranks_per_node}",
                f"#SBATCH --cpus-per-task={first_task.resources.threads}",
                f"#SBATCH --output={bench.benchmark_id}.out",
                f"#SBATCH --error={bench.benchmark_id}.err"
            ]
            
            if first_task.resources.time:
                sb_lines.append(f"#SBATCH --time={first_task.resources.time}")
            if first_task.resources.partition:
                sb_lines.append(f"#SBATCH --partition={first_task.resources.partition}")
            elif self.config and self.config.system.partition:
                sb_lines.append(f"#SBATCH --partition={self.config.system.partition}")
    
            if first_task.resources.account:
                sb_lines.append(f"#SBATCH --account={first_task.resources.account}")
            elif self.config and self.config.system.account:
                sb_lines.append(f"#SBATCH --account={self.config.system.account}")
            if first_task.resources.qos:
                sb_lines.append(f"#SBATCH --qos={first_task.resources.qos}")
            if first_task.resources.gpus > 0:
                sb_lines.append(f"#SBATCH --gpus-per-node={first_task.resources.gpus}")
                
            sb_lines.append("")
            
            # Add commands for all tasks
            # If multiple tasks, we might want to run them sequentially or in parallel (srun &)
            # For now, sequential
            for task in bench.tasks:
                sb_lines.append(f"echo 'Starting task {task.task_id}'")
                sb_lines.append(task.command)
                sb_lines.append("")
            
            script = "\n".join(sb_lines)
            
        # Save script to file
        script_file = os.path.join(first_task.working_directory, f"{bench.benchmark_id}.sh")
        with open(script_file, "w") as f:
            f.write(script)
        
        # Update tasks with script file
        for task in bench.tasks:
            task.script_file = script_file
            self.result_store.save_task(task, run_id)
            
        job = Job(
            job_id=f"job_{bench.benchmark_id}",
            tasks=[t.task_id for t in bench.tasks],
            script_content=script
        )
        
        try:
            scheduler_id = self.scheduler.submit_job(job)
            bench.job_id = scheduler_id
            bench.status = TaskStatus.RUNNING # Or SUBMITTED
            
            # Update tasks
            for task in bench.tasks:
                task.job_id = scheduler_id
                task.status = TaskStatus.RUNNING
                self.result_store.save_task(task, run_id)
                
            logger.info(f"Submitted benchmark {bench.benchmark_id} as job {scheduler_id}")
        except Exception as e:
            logger.error(f"Failed to submit benchmark {bench.benchmark_id}: {e}")
            bench.status = TaskStatus.FAILED
            for task in bench.tasks:
                task.status = TaskStatus.FAILED
                self.result_store.save_task(task, run_id)
