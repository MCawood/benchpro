import json
import os
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

from benchpro.core.domain import ResourceRequest, Task
from benchpro.core.planner import Planner
from benchpro.core.executor import Executor

console = Console()

@click.group()
def suite_cli():
    """Manage benchmark suites"""
    pass

@suite_cli.command(name="plan")
@click.argument("suite_file", type=click.Path(exists=True))
@click.option("--nodes", "-N", type=int, help="Override nodes")
@click.option("--ranks-per-node", "-n", type=int, help="Override ranks per node")
@click.option("--threads", "-c", type=int, help="Override threads per rank")
@click.option("--gpus", "-g", type=int, help="Override GPUs per node")
@click.option("--json", "json_out", is_flag=True, help="Output plan as JSON")
@click.pass_context
def plan_suite(ctx, suite_file, nodes, ranks_per_node, threads, gpus, json_out):
    """Plan a suite execution"""
    try:
        with open(suite_file, "r") as f:
            suite_data = yaml.safe_load(f)
            
        suite_id = suite_data.get("name", "unknown_suite")
        matrix = suite_data.get("matrix", {})
        
        # Apply overrides
        if nodes:
            matrix["nodes"] = [nodes]
        if ranks_per_node:
            matrix["ranks_per_node"] = [ranks_per_node]
        if threads:
            matrix["threads"] = [threads]
        if gpus:
            matrix["gpus"] = [gpus]
            
        base_res = suite_data.get("resources", {})
        
        command_template = suite_data.get("command")
        requirements = suite_data.get("requirements")
        tasks = Planner.expand_matrix(suite_id, matrix, base_res, command_template, requirements)
        
        if json_out:
            tasks_data = [t.model_dump() for t in tasks]
            console.print_json(data=tasks_data)
        else:
            table = Table(title=f"Plan for {suite_id}")
            table.add_column("Task ID", style="cyan")
            table.add_column("Nodes", justify="right")
            table.add_column("Ranks", justify="right")
            table.add_column("Threads", justify="right")
            table.add_column("GPUs", justify="right")
            table.add_column("Params")
            
            for t in tasks:
                table.add_row(
                    t.task_id,
                    str(t.resources.nodes),
                    str(t.resources.ranks_per_node),
                    str(t.resources.threads),
                    str(t.resources.gpus),
                    str(t.parameters)
                )
            console.print(table)
            console.print(f"\nTotal tasks: {len(tasks)}")
            
    except Exception as e:
        console.print(f"[red]Error planning suite: {e}[/red]")
        if not json_out:
            raise

@suite_cli.command(name="run")
@click.argument("suite_file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Simulate execution")
@click.pass_context
def run_suite(ctx, suite_file, dry_run):
    """Run a benchmark suite"""
    # For now, just re-plan and run. In future, we might load a plan file.
    # This duplicates some logic from plan, but that's okay for now.
    try:
        with open(suite_file, "r") as f:
            suite_data = yaml.safe_load(f)
            
        suite_id = suite_data.get("name", "unknown_suite")
        matrix = suite_data.get("matrix", {})
        base_res = suite_data.get("resources", {})
        
        command_template = suite_data.get("command")
        requirements = suite_data.get("requirements")
        tasks = Planner.expand_matrix(suite_id, matrix, base_res, command_template, requirements)
        
        if dry_run:
            console.print("[yellow]Dry run enabled. Tasks that would run:[/yellow]")
            for t in tasks:
                console.print(f"  {t.task_id}: {t.command}")
            return

        # Default to local for now, could expose via flag
        executor = Executor(backend="local")
        import asyncio
        asyncio.run(executor.run_tasks(tasks, suite_id=suite_id))
        
    except Exception as e:
        console.print(f"[red]Error running suite: {e}[/red]")
