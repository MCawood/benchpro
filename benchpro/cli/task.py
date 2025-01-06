"""Task management commands for BenchPRO CLI."""

import asyncio
import click
from pathlib import Path
import re
from typing import Dict, List
from benchpro.core.domain import Task, TaskState
from benchpro.core.validation.validators import validate_memory_string, FileValidator
from benchpro.core.executor.local import LocalExecutor

@click.group()
def task():
    """Manage BenchPRO tasks."""
    pass

@task.command()
@click.argument('directory', type=click.Path())
def init(directory):
    """Initialize a BenchPRO workspace."""
    try:
        workspace = Path(directory)
        tasks_dir = workspace / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"Initialized BenchPRO workspace in {workspace}")
    except Exception as e:
        raise click.ClickException(str(e))

def get_workspace_dir():
    """Get the workspace directory from context or use current directory."""
    ctx = click.get_current_context()
    if ctx.obj and 'cwd' in ctx.obj:
        return Path(ctx.obj['cwd'])
    return Path.cwd()

def validate_workspace():
    """Validate that we're in a BenchPRO workspace."""
    workspace = get_workspace_dir()
    tasks_dir = workspace / 'tasks'
    if not tasks_dir.exists():
        raise click.ClickException("Not in a BenchPRO workspace")
    return workspace

def validate_task_name(name: str) -> str:
    """Validate task name contains only allowed characters.
    
    Args:
        name: The task name to validate.
        
    Returns:
        str: The validated task name.
        
    Raises:
        click.ClickException: If the task name contains invalid characters.
    """
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', name):
        raise click.ClickException(
            "Invalid task name. Use only letters, numbers, underscores, and hyphens. "
            "Must start with a letter or number."
        )
    return name

def get_task(name: str) -> Task:
    """Get a task by name.
    
    Args:
        name: The name of the task to retrieve.
        
    Returns:
        Task: The task object with the specified name.
        
    Raises:
        click.ClickException: If the task does not exist.
    """
    workspace = validate_workspace()
    task_dir = workspace / 'tasks' / name
    if not task_dir.exists():
        raise click.ClickException(f"Task '{name}' not found")
    
    # Find template path from task directory
    template_path = None
    for file in task_dir.glob('*.sh'):
        if file.is_file():
            template_path = file
            break
    
    # Load task state from file
    state_data = Task.load_state(task_dir)
    
    return Task(
        name=name,
        working_dir=task_dir,
        template_path=template_path,
        state=state_data["state"],
        error=state_data["error"]
    )

def parse_env_vars(env_vars: List[str]) -> Dict[str, str]:
    """Parse environment variables from CLI arguments.
    
    Args:
        env_vars: List of environment variable strings in KEY=VALUE format.
        
    Returns:
        Dict[str, str]: Dictionary of environment variables.
        
    Raises:
        click.ClickException: If any environment variable has invalid format.
    """
    result = {}
    for var in env_vars:
        try:
            key, value = var.split('=', 1)
            result[key] = value
        except ValueError:
            raise click.ClickException(f"Invalid environment variable format: {var}")
    return result

def run_async(coro):
    """Run an async coroutine in the event loop.
    
    This helper function manages the event loop lifecycle for running
    async coroutines from synchronous Click commands.
    
    Args:
        coro: The coroutine to run.
        
    Returns:
        The result of the coroutine execution.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=5.0))
    except asyncio.TimeoutError:
        raise click.ClickException("Operation timed out")
    finally:
        if not loop.is_running():
            loop.close()

async def _run_task(task: Task, executor: LocalExecutor) -> None:
    """Run a task using the provided executor.
    
    Args:
        task: The task to run.
        executor: The executor to use for running the task.
        
    Raises:
        click.ClickException: If the task fails to run.
    """
    try:
        await executor.run(task)
        # Wait for task to complete with timeout
        try:
            while True:
                state = await asyncio.wait_for(executor.status(task), timeout=1.0)
                if state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                    break
                await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            # Task is still running, which is fine
            pass
            
    except Exception as e:
        await executor.cleanup(task)
        raise click.ClickException(f"Failed to run task: {str(e)}")

async def _get_task_status(task: Task, executor: LocalExecutor) -> TaskState:
    """Get task status using the provided executor.
    
    Args:
        task: The task to check.
        executor: The executor to use for checking status.
        
    Returns:
        TaskState: The current state of the task.
    """
    try:
        return await asyncio.wait_for(executor.status(task), timeout=1.0)
    except asyncio.TimeoutError:
        raise click.ClickException("Failed to get task status: Operation timed out")

async def _stop_task(task: Task, executor: LocalExecutor) -> None:
    """Stop a task using the provided executor.
    
    Args:
        task: The task to stop.
        executor: The executor to use for stopping the task.
        
    Raises:
        click.ClickException: If the task is not running.
    """
    state = await executor.status(task)
    if state != TaskState.RUNNING:
        raise click.ClickException(f"Task '{task.name}' is not running")
    await executor.stop(task)

@task.command()
@click.argument('name')
@click.option('--template', '-t', type=click.Path(exists=True, dir_okay=False),
              help='Path to task template script')
@click.option('--working-dir', '-d', type=click.Path(),
              help='Working directory for the task')
@click.option('--cores', '-c', type=int, default=1,
              help='Number of CPU cores required')
@click.option('--memory', '-m', type=str, default="1G",
              help='Memory requirement (e.g., 1G, 512M)')
@click.option('--walltime', '-w', type=int, default=3600,
              help='Wall time limit in seconds')
def create(name, template, working_dir, cores, memory, walltime):
    """Create a new task with the given parameters."""
    try:
        # Validate task name
        name = validate_task_name(name)
        
        # Validate memory format
        try:
            validate_memory_string(memory)
        except ValueError as e:
            raise click.ClickException(f"Invalid memory format: {e}")
        
        # Use provided working directory or default to workspace/tasks/name
        if working_dir:
            task_dir = Path(working_dir)
        else:
            workspace = validate_workspace()
            task_dir = workspace / 'tasks' / name
        
        # Create task directory
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a default template if none provided
        template_path = None
        if template:
            # Validate template file
            validator = FileValidator(extensions=[".sh"])
            try:
                template_path = validator(Path(template))
                # Copy template to task directory
                import shutil
                dest_path = task_dir / template_path.name
                shutil.copy2(template_path, dest_path)
                template_path = dest_path
            except ValueError as e:
                raise click.ClickException(f"Invalid template file: {e}")
            except Exception as e:
                raise click.ClickException(f"Failed to copy template file: {str(e)}")
        
        task = Task(
            name=name,
            working_dir=task_dir,
            template_path=template_path,
            variables={
                'cores': cores,
                'memory': memory,
                'walltime': walltime
            }
        )
        
        click.echo(f"Task '{name}' created successfully")
        click.echo(f"Working directory: {task_dir}")
        click.echo(f"Resources: {cores} cores, {memory} memory, {walltime}s walltime")
        
    except Exception as e:
        raise click.ClickException(str(e))

@task.command()
def list():
    """List all tasks."""
    try:
        workspace = validate_workspace()
        tasks_dir = workspace / 'tasks'
        tasks = [d.name for d in tasks_dir.iterdir() if d.is_dir()]
        if not tasks:
            click.echo("No tasks found")
            return
        for task_name in sorted(tasks):
            click.echo(task_name)
    except Exception as e:
        raise click.ClickException(str(e))

@task.command()
@click.argument('name')
@click.option('--env', '-e', multiple=True,
              help='Environment variables in KEY=VALUE format')
def run(name, env):
    """Run a task."""
    try:
        workspace = validate_workspace()
        task = get_task(name)
        env_vars = parse_env_vars(env) if env else {}
        executor = LocalExecutor(workspace, env=env_vars)
        run_async(_run_task(task, executor))
        click.echo(f"Started task '{name}'")
    except Exception as e:
        raise click.ClickException(str(e))

@task.command()
@click.argument('name')
def status(name):
    """Check task status."""
    try:
        task = get_task(name)
        executor = LocalExecutor(task.working_dir)
        state = run_async(_get_task_status(task, executor))
        
        status_messages = {
            TaskState.CREATED: "CREATED",
            TaskState.PENDING: "PENDING",
            TaskState.RUNNING: "RUNNING", 
            TaskState.COMPLETED: "COMPLETED",
            TaskState.FAILED: "FAILED",
            TaskState.CANCELLED: "CANCELLED"
        }
        
        click.echo(f"Task '{name}' is {status_messages[state]}")
        
        if state == TaskState.FAILED and task.error:
            click.echo(f"Error: {task.error}")
            ctx = click.get_current_context()
            ctx.exit(1)
            
    except Exception as e:
        raise click.ClickException(str(e))

@task.command()
@click.argument('name')
def stop(name):
    """Stop a running task."""
    try:
        task = get_task(name)
        executor = LocalExecutor(task.working_dir)
        run_async(_stop_task(task, executor))
        click.echo(f"Stopped task '{name}'")
    except Exception as e:
        raise click.ClickException(str(e))