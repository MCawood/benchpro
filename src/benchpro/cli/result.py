import click
from benchpro.core.services.capture import CaptureService
from benchpro.core.results import ResultStore
from benchpro.core.domain import Task
from benchpro.core.exceptions import BenchProError

@click.group(name="result")
def result_cli():
    """Manage benchmark results."""
    pass

@result_cli.command()
@click.argument("task_id")
def submit(task_id):
    """Submit a task result to the server."""
    store = ResultStore()
    task_data = store.get_task(task_id)
    
    if not task_data:
        raise BenchProError(f"Task {task_id} not found")
        
    # Reconstruct Task object
    # Note: We might need a better way to hydrate Task objects from DB dicts
    # For now, we do a best-effort reconstruction for the purpose of submission
    task = Task(**task_data)
    
    service = CaptureService(store)
    service.capture_result(task)
