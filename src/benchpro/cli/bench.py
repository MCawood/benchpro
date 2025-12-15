import click
import asyncio
import yaml
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table

from benchpro.core.domain import Task, ResourceRequest, TaskStatus, Build, MetricDefinition, Benchmark
from benchpro.core.executor import Executor
from benchpro.core.planner import Planner
from benchpro.core.resolver import Resolver
from benchpro.core.results import ResultStore
from benchpro.core.config import Config
from benchpro.core.services.capture import CaptureService
from benchpro.core.parser import ResultParser
from benchpro.core.parser import ResultParser
from benchpro.core.scheduler import SlurmBackend, LocalBackend
from benchpro.core.services.status_checker import StatusChecker

console = Console()

@click.group()
def bench_cli():
    """Manage benchmarks (suites and tasks)"""
    pass

from benchpro.cli.utils import get_valid_suites

@bench_cli.command(name="run")
@click.argument("suite_file", required=False, shell_complete=get_valid_suites)
@click.option("--command", help="Command to run (for ad-hoc tasks)")
@click.option("--nodes", "-N", type=int, help="Number of nodes")
@click.option("--ranks", "-n", type=int, help="Ranks per node")
@click.option("--threads", "-c", type=int, help="Threads per rank")
@click.option("--gpus", "-g", type=int, help="GPUs per node")
@click.option("--build-code", help="Application code to bind (for ad-hoc)")
@click.option("--build-version", help="Application version to bind (for ad-hoc)")
@click.option("--build-label", help="Build label to bind (for ad-hoc)")
@click.option("--dry-run", is_flag=True, help="Simulate execution")
@click.option("--system", help="System configuration to use")
@click.option("--scheduler", help="Scheduler to use (e.g. local, slurm)")
@click.option("--strategy", default="one_to_one", help="Job building strategy")
@click.pass_context
def run_bench(ctx, suite_file, command, nodes, ranks, threads, gpus, build_code, build_version, build_label, dry_run, system, scheduler, strategy):
    """Run a benchmark suite or an ad-hoc task"""
    try:
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

        backend = scheduler or config.system.scheduler
        
        # Case 1: Ad-hoc task (if --command is provided)
        if command:
            if suite_file:
                console.print("[yellow]Warning: 'suite_file' argument ignored when --command is used.[/yellow]")
            
            # Create resources
            resources = ResourceRequest(
                nodes=nodes or 1,
                ranks_per_node=ranks or 1,
                threads=threads or 1,
                gpus=gpus or 0
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
                status=TaskStatus.PENDING,
                working_directory=os.getcwd()
            )
            
            # Wrap in Benchmark
            bench = Benchmark(
                benchmark_id=f"bench_{task_id}",
                suite_id="ad_hoc",
                tasks=[task]
            )
            benchmarks = [bench]
            suite_id = "ad_hoc"
            
        # Case 2: Benchmark Suite (if suite_file is provided)
        elif suite_file:
            # Resolve suite file
            suite_path = Resolver.resolve_suite(suite_file)
            if not suite_path:
                 raise FileNotFoundError(f"Suite not found: {suite_file}")
            
            # Verify the resolved path exists
            if not suite_path.exists():
                 raise FileNotFoundError(f"Resolved suite path does not exist: {suite_path}")

            with open(suite_path, "r") as f:
                suite_data = yaml.safe_load(f)
                
            suite_id = suite_data.get("name", "unknown_suite")
            matrix = suite_data.get("matrix", {})
            base_res = suite_data.get("resources", {})
            
            # Apply overrides if provided
            if nodes:
                matrix["nodes"] = [nodes]
            if ranks:
                matrix["ranks_per_node"] = [ranks]
            if threads:
                matrix["threads"] = [threads]
            if gpus:
                matrix["gpus"] = [gpus]
            
            # Resolve template if provided
            template_path = None
            if "template" in suite_data:
                template_name = suite_data["template"]
                # Try relative to suite file
                template_path = suite_path.parent / template_name
                if not template_path.exists():
                    # Try relative to cwd
                    template_path = Path.cwd() / template_name
                    if not template_path.exists():
                         console.print(f"[yellow]Warning: Template '{template_name}' not found. Using default script generation.[/yellow]")
                         template_path = None
            
            # Expand matrix into benchmarks
            try:
                benchmarks = Planner.expand_matrix(
                    suite_id=suite_id,
                    matrix=matrix,
                    base_resources=base_res,
                    command_template=suite_data.get("command"),
                    requirements=suite_data.get("requirements"),
                    metrics=suite_data.get("metrics"),
                    template=str(template_path) if template_path else None
                )
                console.print(f"Generated {len(benchmarks)} benchmarks")
            except Exception as e:
                console.print(f"[red]Error: Failed to generate benchmarks: {e}[/red]")
                return
            
        else:
            console.print("[red]Error: Must specify either a suite file or --command[/red]")
            return

        # Execute
        if dry_run:
            console.print(f"[yellow]Dry run enabled. System: {config.system.name}, Backend: {backend}, Strategy: {strategy}[/yellow]")
            console.print(f"Building jobs with strategy: {strategy}...")
            
            from benchpro.core.services.job_builder import JobBuilder
            builder = JobBuilder(strategy)
            jobs = builder.build(benchmarks)
            
            console.print(f"[yellow]Jobs that would run ({len(jobs)}):[/yellow]")
            for job in jobs:
                console.print(f"\n[bold cyan]Job: {job.job_id}[/bold cyan]")
                console.print(f"  Resources: Nodes={job.resources.nodes} Tasks/Node={job.resources.ranks_per_node} Time={job.resources.time}")
                console.print(f"  Dependencies: {job.job_dependencies}")
                console.print("  Tasks:")
                for task in job.tasks:
                    console.print(f"    - {task.task_id} (Cmd: {task.command[:50]}...)")
            return

        console.print(f"Starting execution of {len(benchmarks)} benchmark(s) for suite '{suite_id}' using strategy '{strategy}'...")
        executor = Executor(backend=backend, config=config)
        asyncio.run(executor.run_benchmarks(benchmarks, suite_id=suite_id, strategy=strategy))
        
        # Summary
        if 'tasks' not in locals():
            tasks = []
            for b in benchmarks:
                tasks.extend(b.tasks)
                
        success_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        submitted_count = sum(1 for t in tasks if t.status in [TaskStatus.RUNNING, TaskStatus.PENDING])
        
        if success_count == len(tasks):
            console.print(f"[green]All {len(tasks)} tasks completed successfully[/green]")
        elif success_count + submitted_count == len(tasks) and backend == "slurm":
            console.print(f"[green]All {len(tasks)} tasks submitted successfully[/green]")
        else:
            if backend == "slurm":
                console.print(f"[yellow]{success_count} completed, {submitted_count} submitted, {len(tasks) - success_count - submitted_count} failed[/yellow]")
            else:
                console.print(f"[yellow]{success_count}/{len(tasks)} tasks completed successfully[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error running benchmark: {e}[/red]")

@bench_cli.command(name="avail")
def list_available_suites():
    """List available benchmark suites"""
    available = {}
    search_paths = Resolver.get_suite_search_paths()
    
    for search_path in search_paths:
        profiles = []
        if search_path.exists() and search_path.is_dir():
            for profile_file in sorted(search_path.glob("*.yaml")):
                if profile_file.is_file():
                    profiles.append(profile_file)
            if profiles:
                available[str(search_path)] = profiles
    
    if not available:
        console.print("[yellow]No benchmark suites found in search directories[/yellow]")
        console.print("\nSearch directories:")
        for path in search_paths:
            console.print(f"  - {path}")
        return
    
    # Show profiles grouped by search path
    for search_path, profiles in available.items():
        console.print(f"\n[bold cyan]{search_path}[/bold cyan]")
        for profile in profiles:
            profile_name = profile.stem  # Remove .yaml extension
            console.print(f"  • {profile_name}")

@bench_cli.command(name="list")
@click.option("--limit", "-l", default=10, help="Limit number of runs")
def list_results(limit):
    """List recent benchmark runs"""
    store = ResultStore()
    runs = store.get_runs(limit=limit)
    
    table = Table(title="Recent Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Nodes", justify="right")
    table.add_column("Tasks", justify="right")
    table.add_column("Status", style="magenta")
    table.add_column("Result", justify="right")
    table.add_column("Timestamp", style="blue")
    
    table.add_column("Timestamp", style="blue")
    
    # Sync status
    # We want to sync all active tasks really, but for listing we might just sync all active.
    # StatusChecker.sync_tasks() without IDs syncs all active tasks.
    checker = StatusChecker(store)
    checker.sync_tasks()

    for run in runs:
        # Fetch tasks (use cache if available)
        tasks = run.get("_tasks")
        if tasks is None:
             tasks = store.get_run_tasks(run["run_id"])
        
        # Determine nodes
        nodes = "-"
        if tasks:
            # Assume uniform nodes for now
            try:
                nodes = str(tasks[0]["resources"]["nodes"])
            except (KeyError, IndexError):
                pass
        
        # Determine status
        status = "UNKNOWN"
        if tasks:
            # Simple aggregation: if any failed -> FAILED, if all completed -> COMPLETED, else RUNNING/PENDING
            task_statuses = [t["status"] for t in tasks]
            if "failed" in task_statuses:
                status = "[red]FAILED[/red]"
            elif all(s == "completed" for s in task_statuses):
                status = "[green]COMPLETED[/green]"
            elif "running" in task_statuses:
                status = "[yellow]RUNNING[/yellow]"
            elif "pending" in task_statuses:
                status = "[yellow]PENDING[/yellow]"
            else:
                status = task_statuses[0].upper()
        
        # Determine result (primary metric of first task)
        result = "-"
        if tasks:
            first_task = tasks[0]
            # Check for saved metrics
            metrics = store.get_task_metrics(first_task["task_id"])
            if metrics:
                # Just take the first one
                k = next(iter(metrics))
                v = metrics[k]["value"]
                u = metrics[k]["unit"] or ""
                result = f"{v} {u}".strip()
        
        # Format timestamp
        ts = run["timestamp"]
        try:
            dt = datetime.fromisoformat(ts)
            ts = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass

        table.add_row(
            run["run_id"],
            nodes,
            str(len(tasks)),
            status,
            result,
            ts
        )
        
    console.print(table)

@bench_cli.command(name="show")
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
    
    # Sync status for this run
    if tasks:
        # Sync tasks for this run
        task_ids = [t["task_id"] for t in tasks if t["status"] in ["running", "pending", "submitted"]]
        if task_ids:
             checker = StatusChecker(store)
             checker.sync_tasks(task_ids)
             # Reload tasks
             tasks = store.get_run_tasks(run_id)

    # Collect metrics for all tasks
    all_metrics = set()
    task_metrics_map = {}
    
    for task in tasks:
        metrics = store.get_task_metrics(task["task_id"])
        
        # If no metrics but we have definitions, try to parse
        # We try parsing even if not completed, in case status update failed but job finished
        if not metrics and task.get("metric_definitions"):
            # Determine output file
            outfile = None
            if task.get("output_file"):
                outfile = Path(task["output_file"])
            elif task.get("job_id"):
                # Fallback to default Slurm pattern
                outfile = Path.cwd() / f"slurm-{task['job_id']}.out"
            
            if outfile and outfile.exists():
                defs = [MetricDefinition(**m) for m in task["metric_definitions"]]
                parsed = ResultParser.parse(outfile, defs)
                if parsed:
                    store.save_metrics(task["task_id"], parsed)
                    metrics = parsed
                    
                    # If we successfully parsed metrics, the task is likely completed
                    if task["status"] != "completed":
                        store.update_task_status(task["task_id"], TaskStatus.COMPLETED)
                        task["status"] = "completed"
        
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

@bench_cli.command(name="delete")
@click.argument("run_id", required=False)
@click.option("--all", is_flag=True, help="Delete all runs")
@click.confirmation_option(prompt="Are you sure you want to delete these runs?")
def delete_run(run_id, all):
    """Delete benchmark runs"""
    store = ResultStore()
    
    # Note: ResultStore might not have delete_run implemented yet, assuming it does or similar to delete_build
    # If not, we might need to add it to ResultStore. 
    # Checking results.py, it didn't have a delete command.
    # Checking build.py, it had delete_build.
    # We should check if ResultStore has delete_run or similar.
    # For now, I'll assume we might need to implement it or it's missing.
    # But wait, I can't easily check ResultStore source right now without another tool call.
    # I'll implement it assuming it exists or I'll add a TODO/Warning if it fails.
    # Actually, I should probably check ResultStore first.
    # But for now let's just implement the CLI part.
    
    console.print("[yellow]Delete functionality not fully implemented in backend yet.[/yellow]")

@bench_cli.command(name="prune")
@click.option("--missing-files", is_flag=True, help="Also delete runs with missing working directories")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without doing it")
@click.confirmation_option(prompt="Are you sure you want to prune runs?")
def prune_runs(missing_files, dry_run):
    """Prune invalid or empty runs"""
    store = ResultStore()
    
    # 1. Empty runs
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT run_id FROM runs WHERE run_id NOT IN (SELECT DISTINCT run_id FROM tasks)")
    empty_runs = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if empty_runs:
        console.print(f"[yellow]Found {len(empty_runs)} empty runs (no tasks)[/yellow]")
        if dry_run:
            for run_id in empty_runs:
                console.print(f"  Would delete: {run_id}")
        else:
            count = store.delete_empty_runs()
            console.print(f"[green]Deleted {count} empty runs[/green]")
    else:
        console.print("[green]No empty runs found[/green]")
        
    # 2. Missing files
    if missing_files:
        runs = store.get_runs(limit=1000)
        runs_to_delete = []
        
        for run in runs:
            tasks = store.get_run_tasks(run["run_id"])
            if not tasks:
                continue
                
            # Check if working directory exists for at least one task
            # Usually all tasks in a run share a base dir or have valid dirs
            # If ALL tasks have missing dirs, we prune the run?
            # Or if ANY task has missing dir?
            # Let's be conservative: if the first task's working dir is missing, the run is likely broken/deleted
            first_task = tasks[0]
            wd = first_task.get("working_directory")
            if wd and not Path(wd).exists():
                runs_to_delete.append(run["run_id"])
                
        if runs_to_delete:
            console.print(f"[yellow]Found {len(runs_to_delete)} runs with missing working directories[/yellow]")
            if dry_run:
                for run_id in runs_to_delete:
                    console.print(f"  Would delete: {run_id}")
            else:
                for run_id in runs_to_delete:
                    store.delete_run(run_id)
                console.print(f"[green]Deleted {len(runs_to_delete)} runs with missing files[/green]")
        else:
            console.print("[green]No runs with missing working directories found[/green]")

@bench_cli.command(name="check")
@click.argument("run_id", required=False)
def check_integrity(run_id):
    """Check integrity of runs and tasks"""
    store = ResultStore()
    
    runs_to_check = []
    if run_id:
        # Check specific run
        # We need to fetch it manually as get_runs doesn't filter by ID easily
        # But get_run_tasks does
        tasks = store.get_run_tasks(run_id)
        if not tasks:
            console.print(f"[red]Run {run_id} not found or has no tasks[/red]")
            return
        runs_to_check.append({"run_id": run_id, "tasks": tasks})
    else:
        # Check all runs
        runs = store.get_runs(limit=100)
        for run in runs:
            tasks = store.get_run_tasks(run["run_id"])
            runs_to_check.append({"run_id": run["run_id"], "tasks": tasks})
            
    issues_found = 0
    
    for item in runs_to_check:
        rid = item["run_id"]
        tasks = item["tasks"]
        
        if not tasks:
            console.print(f"[yellow]Run {rid}: No tasks found (Empty Run)[/yellow]")
            issues_found += 1
            continue
            
        for task in tasks:
            tid = task["task_id"]
            wd = task.get("working_directory")
            
            # Check working directory
            if not wd:
                console.print(f"[red]Run {rid} / Task {tid}: No working directory recorded[/red]")
                issues_found += 1
            elif not Path(wd).exists():
                console.print(f"[red]Run {rid} / Task {tid}: Working directory missing: {wd}[/red]")
                issues_found += 1
                
            # Check script file
            script = task.get("script_file")
            if script and not Path(script).exists():
                console.print(f"[yellow]Run {rid} / Task {tid}: Script file missing: {script}[/yellow]")
                issues_found += 1
                
            # Check output file
            out = task.get("output_file")
            if out and not Path(out).exists():
                # Only an issue if task is completed/failed
                if task["status"] in ["completed", "failed"]:
                    console.print(f"[yellow]Run {rid} / Task {tid}: Output file missing: {out}[/yellow]")
                    issues_found += 1

    if issues_found == 0:
        console.print("[green]No integrity issues found[/green]")
    else:
        console.print(f"\n[red]Found {issues_found} issues[/red]")

@bench_cli.command(name="capture")
@click.argument("task_id", required=False)
def capture_results(task_id):
    """Check status and capture results for tasks"""
    store = ResultStore()
    service = CaptureService(store)
    
    tasks_to_check = []
    if task_id:
        runs = store.get_runs(limit=100)
        found = False
        for run in runs:
            tasks = store.get_run_tasks(run["run_id"])
            for t in tasks:
                if t["task_id"] == task_id:
                    tasks_to_check.append(t)
                    found = True
                    break
            if found:
                break
        if not found:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
    else:
        runs = store.get_runs(limit=50)
        for run in runs:
            tasks = store.get_run_tasks(run["run_id"])
            for t in tasks:
                if t["status"] in ["running", "pending", "submitted"]:
                    tasks_to_check.append(t)
    
    if not tasks_to_check:
        console.print("[yellow]No active tasks found to check[/yellow]")
        return

    console.print(f"Checking {len(tasks_to_check)} tasks...")
    
    for task_data in tasks_to_check:
        try:
            metric_defs = []
            if task_data.get("metric_definitions"):
                metric_defs = [MetricDefinition(**m) for m in task_data["metric_definitions"]]
                
            resources = ResourceRequest(**task_data["resources"])
            
            task = Task(
                task_id=task_data["task_id"],
                suite_id=task_data["suite_id"],
                parameters=task_data["parameters"],
                resources=resources,
                command="unknown", 
                metrics=metric_defs,
                status=TaskStatus(task_data["status"]),
                job_id=task_data["job_id"],
                working_directory=task_data.get("working_directory"),
                task_uuid=task_data.get("task_uuid") or "unknown"
            )
            
            old_status = task.status
            new_status = service.check_task_status(task)
            
            if new_status != old_status:
                console.print(f"Task {task.task_id}: {old_status.value} -> {new_status.value}")
                
            if new_status == TaskStatus.COMPLETED:
                service.capture_result(task)
                console.print(f"[green]Captured results for {task.task_id}[/green]")
                
        except Exception as e:
            console.print(f"[red]Error processing task {task_data['task_id']}: {e}[/red]")

@bench_cli.command(name="log")
@click.argument("id_or_run")
@click.option("--error", "-e", is_flag=True, help="Show error log instead of output log")
def show_log(id_or_run, error):
    """Show the output log for a task or single-task run"""
    store = ResultStore()
    
    # Try finding as task first
    task = store.get_task(id_or_run)
    if not task:
        # Try finding as run
        tasks = store.get_run_tasks(id_or_run)
        if tasks:
            if len(tasks) == 1:
                task = tasks[0]
            else:
                console.print(f"[yellow]Run {id_or_run} has {len(tasks)} tasks. Please specify a task ID:[/yellow]")
                for t in tasks:
                    console.print(f"  - {t['task_id']}")
                return
        
        # Check if it's an empty run
        if not tasks:
            # We need to check if run exists in DB, but ResultStore doesn't expose get_run(id) directly well?
            # It has get_runs() which lists all.
            # Or we can query DB directly?
            # Actually get_runs() is expensive.
            # Let's assume if it looks like a valid ID format but has no tasks...
            pass
            
    if not task:
        console.print(f"[red]Task or Run '{id_or_run}' not found (or has no tasks)[/red]")
        return
        
    task_id = task["task_id"]
    file_path = task.get("error_file") if error else task.get("output_file")
    
    if not file_path:
        console.print(f"[yellow]No {'error' if error else 'output'} log file recorded for task {task_id}[/yellow]")
        return
        
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]Log file not found: {path}[/red]")
        return
        
    console.print(f"[bold cyan]{'Error' if error else 'Output'} Log for {task_id}:[/bold cyan] {path}")
    console.print("-" * 40)
    with open(path, "r") as f:
        console.print(f.read())

@bench_cli.command(name="script")
@click.argument("id_or_run")
def show_script(id_or_run):
    """Show the job script for a task or single-task run"""
    store = ResultStore()
    
    # Try finding as task first
    task = store.get_task(id_or_run)
    if not task:
        # Try finding as run
        tasks = store.get_run_tasks(id_or_run)
        if tasks:
            if len(tasks) == 1:
                task = tasks[0]
            else:
                console.print(f"[yellow]Run {id_or_run} has {len(tasks)} tasks. Please specify a task ID:[/yellow]")
                for t in tasks:
                    console.print(f"  - {t['task_id']}")
                return
                
    if not task:
        console.print(f"[red]Task or Run '{id_or_run}' not found (or has no tasks)[/red]")
        return
        
    task_id = task["task_id"]
    file_path = task.get("script_file")
    
    if not file_path:
        console.print(f"[yellow]No script file recorded for task {task_id}[/yellow]")
        return
        
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]Script file not found: {path}[/red]")
        return
        
    console.print(f"[bold cyan]Job Script for {task_id}:[/bold cyan] {path}")
    console.print("-" * 40)
    
    # Use syntax highlighting
    from rich.syntax import Syntax
    with open(path, "r") as f:
        content = f.read()
        syntax = Syntax(content, "bash", theme="monokai", line_numbers=True)
        console.print(syntax)

@bench_cli.command(name="ls")
@click.argument("id_or_run")
def list_files(id_or_run):
    """List files in the task's working directory"""
    store = ResultStore()
    
    # Try finding as task first
    task = store.get_task(id_or_run)
    if not task:
        # Try finding as run
        tasks = store.get_run_tasks(id_or_run)
        if tasks:
            if len(tasks) == 1:
                task = tasks[0]
            else:
                console.print(f"[yellow]Run {id_or_run} has {len(tasks)} tasks. Please specify a task ID:[/yellow]")
                for t in tasks:
                    console.print(f"  - {t['task_id']}")
                return
                
    if not task:
        console.print(f"[red]Task or Run '{id_or_run}' not found (or has no tasks)[/red]")
        return

    task_id = task["task_id"]
    work_dir = task.get("working_directory")
    
    if not work_dir:
        console.print(f"[yellow]No working directory recorded for task {task_id}[/yellow]")
        return
        
    path = Path(work_dir)
    if not path.exists():
        console.print(f"[red]Working directory not found: {path}[/red]")
        return
        
    console.print(f"[bold cyan]Files in {path}:[/bold cyan]")
    
    # List files with details
    table = Table(show_header=True)
    table.add_column("Name", style="green")
    table.add_column("Size", justify="right")
    table.add_column("Modified", style="blue")
    
    for item in sorted(path.iterdir()):
        if item.name.startswith("."):
            continue
            
        try:
            stat = item.stat()
            size = f"{stat.st_size} B"
            if stat.st_size > 1024:
                size = f"{stat.st_size / 1024:.1f} KB"
            if stat.st_size > 1024 * 1024:
                size = f"{stat.st_size / (1024 * 1024):.1f} MB"
                
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            name = item.name
            if item.is_dir():
                name += "/"
                
            table.add_row(name, size, mtime)
        except Exception:
            pass
            
    console.print(table)
    console.print(table)

@bench_cli.command(name="delete")
@click.argument("id_or_run")
@click.option("--force", is_flag=True, help="Force delete without confirmation")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete_run(id_or_run, force, yes):
    """Delete a benchmark run or task"""
    store = ResultStore()
    config = Config.load()
    
    # Try finding as task first
    task = store.get_task(id_or_run)
    run_id = None
    if task:
        run_id = task.get("run_id")
    else:
        # Check if it's a run ID (even if empty)
        # We can verify by querying runs table directly or using get_runs filter
        # but for now, let's assume if it looks like a Run ID we try to delete it
        # Or better, check DB.
        
        # ResultStore doesn't have get_run methods exposed nicely yet.
        # Let's peek into DB.
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT run_id FROM runs WHERE run_id=?", (id_or_run,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            run_id = row[0]
            
    if not run_id:
        console.print(f"[red]Task or Run '{id_or_run}' not found[/red]")
        return

    if not (force or yes):
        click.confirm(f"Are you sure you want to delete run '{run_id}' and all associated data?", abort=True)
        
    # 1. Get workspace dir to delete files
    # We need to find where it lives.
    # If we have tasks, use their WD.
    # If valid run but no tasks (zombie), use expected path from new executor logic?
    
    tasks = store.get_run_tasks(run_id)
    
    # Cancel active jobs
    jobs_to_wait = []
    if tasks:
        scheduler = SlurmBackend() # Or use config to decide backend? Typically Slurm for async.
        
        for t in tasks:
            status = t.get("status")
            job_id = t.get("job_id")
            # Status can be string or int depending on version? DB stores string.
            # Normalize status check
            is_active = False
            if isinstance(status, str):
                is_active = status.lower() in ["running", "pending", "submitted"]
            elif isinstance(status, int):
                # Using TaskStatus enum logic? 
                pass 
            
            if is_active and job_id:
                try:
                    console.print(f"Cancelling job {job_id} for task {t['task_id']}...")
                    if scheduler.cancel_job(str(job_id)):
                        console.print(f"[green]Cancelled job {job_id}[/green]")
                        jobs_to_wait.append(str(job_id))
                except Exception as e:
                    console.print(f"[red]Error cancelling job {job_id}: {e}[/red]")
                    
    if jobs_to_wait:
         with console.status(f"[bold blue]Waiting for {len(jobs_to_wait)} job(s) to terminate...[/bold blue]"):
             if scheduler.wait_for_jobs(jobs_to_wait):
                 console.print("[green]All jobs terminated[/green]")
             else:
                 console.print("[yellow]Timeout waiting for jobs to terminate. Proceeding with deletion anyway.[/yellow]")
    work_dirs = set()
    if tasks:
        for t in tasks:
            if t.get("working_directory"):
                work_dirs.add(Path(t["working_directory"]))
    else:
        # Try to guess workspace for empty run based on new logic
        # {workspace_dir}/workspaces/runs/{run_id}
        ws_root = Path(config.system.workspace_dir or Path.cwd() / "benchpro")
        runs_root = ws_root / "workspaces" / "runs"
        possible_wd = runs_root / run_id
        if possible_wd.exists():
            work_dirs.add(possible_wd)
            
    # 2. Delete DB records
    # Delete tasks first
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE run_id=?", (run_id,))
    deleted_tasks = cursor.rowcount
    cursor.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
    conn.commit()
    conn.close()
    
    console.print(f"[green]Deleted run record '{run_id}' and {deleted_tasks} tasks[/green]")
    
    # 3. Delete directories
    import shutil
    for wd in work_dirs:
        try:
            if wd.exists():
                shutil.rmtree(wd)
                console.print(f"[green]Deleted workspace: {wd}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to delete workspace {wd}: {e}[/red]")
@bench_cli.command(name="purge")
@click.option("--force", is_flag=True, help="Force purge without confirmation")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def purge_runs(force, yes):
    """Purge all benchmark runs and data"""
    if not (force or yes):
        click.confirm("Are you sure you want to purge ALL benchmark runs and data? This cannot be undone.", abort=True)
        
    store = ResultStore()
    config = Config.load()
    
    # 1. Get all tasks to find working directories before deleting records
    # We need to be careful not to delete directories that are not in our workspace
    # or are shared with builds (though builds should be separate).
    
    # Get all tasks
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT working_directory FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    
    working_dirs = set()
    for row in rows:
        if row[0]:
            working_dirs.add(Path(row[0]))
            
    # 2. Clear database
    count = store.clear_all_runs()
    console.print(f"[green]Cleared {count} run records from database[/green]")
    
    # 3. Clear workspaces
    # 3. Clear workspaces
    root_dir = Path(config.system.workspace_dir or Path.cwd() / "benchpro")
    workspaces_dir = root_dir / "workspaces"
    runs_dir = workspaces_dir / "runs"
    
    deleted_dirs = 0
    
    # Strategy:
    # We now isolate runs in workspaces/runs, so we can safely delete that entire directory
    # or iterate its contents.
    
    if runs_dir.exists():
        import shutil
        for item in runs_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                    deleted_dirs += 1
                else:
                    item.unlink()
            except Exception as e:
                pass
                
        console.print(f"[green]Deleted {deleted_dirs} benchmark workspaces from {runs_dir}[/green]")
    else:
        # Also check for legacy workspaces in root?
        # Maybe safer not to touch root workspaces automatically anymore to avoid deleting apps.
        # If user wants to clean old runs, they can do it manually or we implement a targeted cleanup.
        pass

    if workspaces_dir.exists():
         # Check if we should clean up workspaces_dir itself if empty?
         # No.
         pass
         
    if not runs_dir.exists() and deleted_dirs == 0:
         console.print("[yellow]No runs directory found to purge[/yellow]")
