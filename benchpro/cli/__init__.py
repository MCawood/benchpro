"""
BenchPRO Command Line Interface.

This module provides the command-line interface for BenchPRO,
allowing users to create and manage tasks and jobs.
"""

import click
from pathlib import Path
from .task import task  # Import the task command group

def get_workspace_dir():
    """Get the workspace directory from context or use current directory."""
    ctx = click.get_current_context()
    if ctx.obj and 'cwd' in ctx.obj:
        return Path(ctx.obj['cwd'])
    return Path.cwd()

@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    """BenchPRO - A benchmark execution and management tool."""
    # Initialize context object if not already done
    ctx.ensure_object(dict)

cli.add_command(task)  # Add the task command group

@cli.command()
@click.argument('directory', type=click.Path(file_okay=False), default='.')
def init(directory):
    """Initialize a new BenchPRO workspace.
    
    Creates necessary directory structure and configuration files.
    """
    workspace_dir = get_workspace_dir() / directory
    
    # Create workspace structure
    workspace_dir.mkdir(exist_ok=True)
    (workspace_dir / 'tasks').mkdir(exist_ok=True)
    (workspace_dir / 'jobs').mkdir(exist_ok=True)
    (workspace_dir / 'templates').mkdir(exist_ok=True)
    
    # Create default config
    config_file = workspace_dir / 'benchpro.yaml'
    if not config_file.exists():
        config_file.write_text("""# BenchPRO Configuration
workspace:
  tasks_dir: tasks
  jobs_dir: jobs
  templates_dir: templates

defaults:
  resources:
    cores: 1
    memory: "1G"
    walltime: 3600
""")
    
    click.echo(f"Initialized BenchPRO workspace in {workspace_dir}")
    click.echo("Created directories: tasks, jobs, templates")
    click.echo("Created default configuration: benchpro.yaml") 