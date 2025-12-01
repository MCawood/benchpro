import click
from rich.console import Console
from rich.table import Table

from pathlib import Path
from benchpro.core.results import ResultStore
from benchpro.core.config import Config
from benchpro.core.scheduler import SlurmBackend, LocalBackend
from benchpro.core.domain import TaskStatus, MetricDefinition
from benchpro.core.parser import ResultParser

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
    
    # Check for running tasks and update status
    tasks_to_check = []
    for task in tasks:
        if task["status"] in ["running", "pending", "submitted"] and task["job_id"]:
            tasks_to_check.append(task)
            
    if tasks_to_check:
        # Load config to get backend
        try:
            config = Config.load()
            # In a real scenario, we'd check which system the run belongs to
            # For now, we assume the current configured system matches the run's system
            # or we just try the configured backend
            
            scheduler = None
            if config.system.scheduler == "slurm":
                scheduler = SlurmBackend()
            else:
                scheduler = LocalBackend()
                
            job_ids = [t["job_id"] for t in tasks_to_check]
            statuses = scheduler.query_job_status(job_ids)
            
            # Update store
            # We need to reconstruct Task objects to save them, or add a method to update status
            # For now, let's just update the dicts and the DB directly if possible, 
            # or use a simplified update approach. 
            # Since ResultStore.save_task takes a Task object, we should probably use that.
            # But we only have dicts here.
            # Let's add a direct update method to ResultStore or reconstruct objects.
            # Reconstructing is safer.
            
            from benchpro.core.domain import Task, ResourceRequest
            
            for task_data in tasks_to_check:
                jid = task_data["job_id"]
                if jid in statuses:
                    new_state = statuses[jid]
                    # Map Slurm state to TaskStatus
                    # COMPLETED -> COMPLETED
                    # FAILED, TIMEOUT, NODE_FAIL -> FAILED
                    # CANCELLED -> CANCELLED
                    # RUNNING -> RUNNING
                    # PENDING -> PENDING
                    
                    mapped_status = TaskStatus.RUNNING # Default
                    if new_state == "COMPLETED":
                        mapped_status = TaskStatus.COMPLETED
                    elif new_state in ["FAILED", "TIMEOUT", "NODE_FAIL", "BOOT_FAIL"]:
                        mapped_status = TaskStatus.FAILED
                    elif new_state.startswith("CANCELLED"):
                        mapped_status = TaskStatus.CANCELLED
                    elif new_state == "PENDING":
                        mapped_status = TaskStatus.PENDING
                    elif new_state == "RUNNING":
                        mapped_status = TaskStatus.RUNNING
                        
                    if mapped_status.value != task_data["status"]:
                        # Update DB
                        # We need to reconstruct the Task object fully to save it
                        # This is a bit heavy, maybe we should add update_task_status to ResultStore
                        # For now, let's do a quick SQL update
                        store.update_task_status(task_data["task_id"], mapped_status)
                        task_data["status"] = mapped_status.value
                        
        except Exception as e:
            console.print(f"[yellow]Failed to update job status: {e}[/yellow]")

        except Exception as e:
            console.print(f"[yellow]Failed to update job status: {e}[/yellow]")

    # Collect metrics for all tasks
    all_metrics = set()
    task_metrics_map = {}
    
    for task in tasks:
        # Get existing metrics
        metrics = store.get_task_metrics(task["task_id"])
        
        # If no metrics but we have definitions and task is completed, try to parse
        if not metrics and task.get("metric_definitions") and task["status"] == "completed":
            job_id = task.get("job_id")
            if job_id:
                # Assume output file is slurm-{job_id}.out in CWD
                # TODO: Handle custom output paths
                outfile = Path.cwd() / f"slurm-{job_id}.out"
                if outfile.exists():
                    # Reconstruct definitions
                    defs = [MetricDefinition(**m) for m in task["metric_definitions"]]
                    parsed = ResultParser.parse(outfile, defs)
                    if parsed:
                        store.save_metrics(task["task_id"], parsed)
                        metrics = parsed
        
        task_metrics_map[task["task_id"]] = metrics
        all_metrics.update(metrics.keys())

    # Add metric columns
    sorted_metrics = sorted(list(all_metrics))
    for metric in sorted_metrics:
        table.add_column(metric, justify="right")

    for task in tasks:
        status_style = "green" if task["status"] == "completed" else "red" if task["status"] == "failed" else "yellow"
        
        row = [
            task["task_id"],
            f"[{status_style}]{task['status']}[/{status_style}]",
            task["job_id"] or "-",
            str(task["exit_code"]) if task["exit_code"] is not None else "-"
        ]
        
        # Add metric values
        metrics = task_metrics_map.get(task["task_id"], {})
        for metric in sorted_metrics:
            if metric in metrics:
                val = metrics[metric]["value"]
                unit = metrics[metric]["unit"]
                if unit:
                    row.append(f"{val} {unit}")
                else:
                    row.append(str(val))
            else:
                row.append("-")
                
        table.add_row(*row)
        
    console.print(table)
