import click
import asyncio
from datetime import datetime
from rich.console import Console

from benchpro.core.domain import Task, ResourceRequest, TaskStatus, Build
from benchpro.core.executor import Executor
from benchpro.core.resolver import Resolver
from benchpro.core.results import ResultStore
from benchpro.core.config import Config

console = Console()

@click.group()
def task_cli():
    """Manage individual tasks"""
    pass

@task_cli.command(name="run")
@click.argument("command")
@click.option("--nodes", default=1, help="Number of nodes")
@click.option("--ranks", default=1, help="Ranks per node")
@click.option("--threads", default=1, help="Threads per rank")
@click.option("--gpus", default=0, help="GPUs per node")
@click.option("--build-code", help="Application code to bind")
@click.option("--build-version", help="Application version to bind")
@click.option("--build-label", help="Build label to bind")
@click.option("--dry-run", is_flag=True, help="Simulate execution")
@click.option("--system", help="System configuration to use")
def run_task(command, nodes, ranks, threads, gpus, build_code, build_version, build_label, dry_run, system):
    """Run a single task immediately"""
    try:
        # Create resources
        resources = ResourceRequest(
            nodes=nodes,
            ranks_per_node=ranks,
            threads=threads,
            gpus=gpus
        )
        
        # Resolve build if requested
        activation_cmd = ""
        if build_code:
            store = ResultStore()
            builds = [Build(**b) for b in store.get_builds()]
            resolver = Resolver(builds)
            
            build = resolver.resolve(
                code=build_code,
                version=build_version,
                build_label=build_label
            )
            
            if build:
                activation_cmd = f"{build.activation_script} && "
                console.print(f"[green]Bound to build: {build.build_id}[/green]")
            else:
                console.print(f"[yellow]Warning: No build found matching code={build_code}[/yellow]")
        
        # Create task
        task_id = f"task_{int(datetime.now().timestamp())}"
        full_command = f"{activation_cmd}{command}"
        
        task = Task(
            task_id=task_id,
            suite_id="ad_hoc",
            resources=resources,
            command=full_command,
            status=TaskStatus.PENDING
        )
        
        if dry_run:
            console.print(f"[yellow]Dry run enabled. Would execute:[/yellow]")
            console.print(f"Task ID: {task_id}")
            console.print(f"Command: {full_command}")
            console.print(f"Resources: {resources}")
            return

        # Execute
        console.print(f"Starting task {task_id}...")
        
        # Load config
        config = Config.load()
        if system:
            if system in config.systems:
                # Override active system
                active_system = config.systems[system]
                merged_system = config.system.model_dump()
                merged_system.update(active_system.model_dump(exclude_unset=True))
                # Update config.system
                from benchpro.core.config import SystemConfig
                config.system = SystemConfig(**merged_system)
            else:
                console.print(f"[yellow]Warning: System '{system}' not found in configuration. Using detected defaults.[/yellow]")
            
        backend = config.system.scheduler
        
        executor = Executor(backend=backend, config=config)
        asyncio.run(executor.run_tasks([task], suite_id="ad_hoc"))
        
        if task.status == TaskStatus.COMPLETED:
            console.print(f"[green]Task completed successfully[/green]")
        else:
            console.print(f"[red]Task failed with exit code {task.exit_code}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error running task: {e}[/red]")
