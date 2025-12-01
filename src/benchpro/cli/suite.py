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
from benchpro.core.config import Config
from benchpro.core.resolver import Resolver

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
        # Resolve suite file
        suite_path = Resolver.resolve_profile(suite_file)
        if not suite_path:
             raise FileNotFoundError(f"Suite not found: {suite_file}")

        with open(suite_path, "r") as f:
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
@click.option("--system", help="System configuration to use")
@click.pass_context
def run_suite(ctx, suite_file, dry_run, system):
    """Run a benchmark suite"""
    # For now, just re-plan and run. In future, we might load a plan file.
    # This duplicates some logic from plan, but that's okay for now.
    try:
        # Resolve suite file
        suite_path = Resolver.resolve_profile(suite_file)
        if not suite_path:
             raise FileNotFoundError(f"Suite not found: {suite_file}")

        with open(suite_path, "r") as f:
            suite_data = yaml.safe_load(f)
            
        suite_id = suite_data.get("name", "unknown_suite")
        matrix = suite_data.get("matrix", {})
        base_res = suite_data.get("resources", {})
        
        command_template = suite_data.get("command")
        requirements = suite_data.get("requirements")
        metrics = suite_data.get("metrics")
        tasks = Planner.expand_matrix(suite_id, matrix, base_res, command_template, requirements, metrics)
        
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

        # Determine backend
        backend = config.system.scheduler
        if dry_run:
            console.print(f"[yellow]Dry run enabled. System: {config.system.name}, Backend: {backend}[/yellow]")
            console.print("[yellow]Tasks that would run:[/yellow]")
            for t in tasks:
                console.print(f"  {t.task_id}: {t.command}")
            return

        executor = Executor(backend=backend, config=config)
        import asyncio
        asyncio.run(executor.run_tasks(tasks, suite_id=suite_id))
        
    except Exception as e:
        console.print(f"[red]Error running suite: {e}[/red]")
