import click
from rich.console import Console
from rich.table import Table

from benchpro.core.results import ResultStore

console = Console()

@click.group()
def results_cli():
    """Manage results"""
    pass

@results_cli.command(name="list")
@click.option("--limit", "-l", default=10, help="Limit number of runs")
def list_results(limit):
    """List recent runs"""
    store = ResultStore()
    runs = store.get_runs(limit=limit)
    
    table = Table(title="Recent Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Suite ID", style="magenta")
    table.add_column("System", style="green")
    table.add_column("Timestamp", style="blue")
    
    for run in runs:
        table.add_row(
            run["run_id"],
            run["suite_id"],
            run["system"],
            run["timestamp"]
        )
        
    console.print(table)

@results_cli.command(name="show")
@click.argument("run_id")
def show_run(run_id):
    """Show details for a specific run"""
    store = ResultStore()
    tasks = store.get_run_tasks(run_id)
    
    if not tasks:
        console.print(f"[yellow]No tasks found for run {run_id}[/yellow]")
        return
        
    table = Table(title=f"Tasks for Run {run_id}")
    table.add_column("Task ID", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Job ID", style="green")
    table.add_column("Exit Code")
    
    for task in tasks:
        status_style = "green" if task["status"] == "completed" else "red" if task["status"] == "failed" else "yellow"
        table.add_row(
            task["task_id"],
            f"[{status_style}]{task['status']}[/{status_style}]",
            task["job_id"] or "-",
            str(task["exit_code"]) if task["exit_code"] is not None else "-"
        )
        
    console.print(table)
