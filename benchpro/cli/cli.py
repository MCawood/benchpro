"""
Command Line Interface for BenchPRO.

This module provides a user-friendly CLI using Click.
"""

import os
import sys
import click
import logging
from typing import Dict, Any, Optional

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.build_executor import BuildExecutor
from benchpro.executor.executor import Executor
from benchpro.results.result_capture import ResultCapture


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('benchpro')


@click.group()
@click.version_option()
def cli():
    """BenchPRO: A benchmark execution and profiling tool."""
    pass


@cli.command()
@click.option(
    "--profile", 
    required=True, 
    help="Profile name to use for the job."
)
@click.option(
    "--output-dir", 
    help="Directory where job outputs will be stored."
)
@click.option(
    "--system", 
    help="System configuration to use."
)
@click.option(
    "--dry-run", 
    is_flag=True, 
    help="Generate job script but don't submit it."
)
@click.option(
    "--executor",
    type=click.Choice(["local", "scheduler"]),
    help="Executor to use for running the job. If not specified, uses the default from configuration."
)
def build(profile: str, output_dir: Optional[str] = None, 
          system: Optional[str] = None, dry_run: bool = False,
          executor: Optional[str] = None):
    """Build and submit a job based on the specified profile."""
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Load default configuration to get default executor
        default_config = config_manager.load_default_config()
        default_executor = default_config.get("execution", {}).get("type", "scheduler")
        
        # Load system configuration if specified
        if system:
            config_manager.load_system_config(system)
        
        # Prepare CLI overrides
        cli_overrides = {}
        if output_dir:
            cli_overrides["job"] = {"output_dir": output_dir}
            
        # Add executor type to CLI overrides if specified, otherwise use default
        if executor:
            cli_overrides["execution"] = {"type": executor}
            # Use the specified executor for output messages
            executor_type = executor
        else:
            # Use the default executor for output messages
            executor_type = default_executor
            
        # Initialize build executor
        build_executor = BuildExecutor(config_manager)
        
        # Execute the build
        success, job_id, script_path = build_executor.execute(profile, cli_overrides, dry_run)
        
        if success:
            click.echo(f"Job script generated: {script_path}")
            
            if dry_run:
                click.echo("Dry run: Job not submitted.")
            else:
                if executor_type == "local":
                    click.echo(f"Job started with PID: {job_id}")
                else:
                    click.echo(f"Job submitted with ID: {job_id}")
        else:
            click.echo("Build failed. See logs for details.", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--profile", 
    required=True, 
    help="Profile name to use for the application build."
)
@click.option(
    "--output-dir", 
    help="Directory where build outputs will be stored."
)
@click.option(
    "--system", 
    help="System configuration to use."
)
@click.option(
    "--dry-run", 
    is_flag=True, 
    help="Generate build script but don't submit it."
)
@click.option(
    "--executor",
    type=click.Choice(["local", "scheduler"]),
    help="Executor to use for running the build. If not specified, uses the default from configuration."
)
def build_app(profile: str, output_dir: Optional[str] = None, 
              system: Optional[str] = None, dry_run: bool = False,
              executor: Optional[str] = None):
    """Build an application based on the specified profile."""
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Load default configuration to get default executor
        default_config = config_manager.load_default_config()
        default_executor = default_config.get("execution", {}).get("type", "scheduler")
        
        # Load system configuration if specified
        if system:
            config_manager.load_system_config(system)
        
        # Prepare CLI overrides
        cli_overrides = {}
        if output_dir:
            cli_overrides["job"] = {"output_dir": output_dir}
            
        # Force task type to application
        cli_overrides["task_type"] = "application"
        
        # Add executor type to CLI overrides if specified, otherwise use default
        if executor:
            cli_overrides["execution"] = {"type": executor}
            # Use the specified executor for output messages
            executor_type = executor
        else:
            # Use the default executor for output messages
            executor_type = default_executor
            
        # Initialize build executor
        build_executor = BuildExecutor(config_manager)
        
        # Execute the build
        success, job_id, script_path = build_executor.execute(profile, cli_overrides, dry_run)
        
        if success:
            click.echo(f"Application build script generated: {script_path}")
            
            if dry_run:
                click.echo("Dry run: Job not submitted.")
            else:
                if executor_type == "local":
                    click.echo(f"Application build started with PID: {job_id}")
                else:
                    click.echo(f"Application build job submitted with ID: {job_id}")
        else:
            click.echo("Application build failed. See logs for details.", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--profile", 
    required=True, 
    help="Profile name to use for the benchmark run."
)
@click.option(
    "--output-dir", 
    help="Directory where benchmark outputs will be stored."
)
@click.option(
    "--system", 
    help="System configuration to use."
)
@click.option(
    "--dry-run", 
    is_flag=True, 
    help="Generate benchmark script but don't submit it."
)
@click.option(
    "--executor",
    type=click.Choice(["local", "scheduler"]),
    help="Executor to use for running the benchmark. If not specified, uses the default from configuration."
)
def run_benchmark(profile: str, output_dir: Optional[str] = None, 
                  system: Optional[str] = None, dry_run: bool = False,
                  executor: Optional[str] = None):
    """Run a benchmark based on the specified profile."""
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Load default configuration to get default executor
        default_config = config_manager.load_default_config()
        default_executor = default_config.get("execution", {}).get("type", "scheduler")
        
        # Load system configuration if specified
        if system:
            config_manager.load_system_config(system)
        
        # Prepare CLI overrides
        cli_overrides = {}
        if output_dir:
            cli_overrides["job"] = {"output_dir": output_dir}
            
        # Force task type to benchmark
        cli_overrides["task_type"] = "benchmark"
        
        # Add executor type to CLI overrides if specified, otherwise use default
        if executor:
            cli_overrides["execution"] = {"type": executor}
            # Use the specified executor for output messages
            executor_type = executor
        else:
            # Use the default executor for output messages
            executor_type = default_executor
            
        # Initialize build executor
        build_executor = BuildExecutor(config_manager)
        
        # Execute the benchmark
        success, job_id, script_path = build_executor.execute(profile, cli_overrides, dry_run)
        
        if success:
            click.echo(f"Benchmark run script generated: {script_path}")
            
            if dry_run:
                click.echo("Dry run: Job not submitted.")
            else:
                if executor_type == "local":
                    click.echo(f"Benchmark started with PID: {job_id}")
                else:
                    click.echo(f"Benchmark job submitted with ID: {job_id}")
        else:
            click.echo("Benchmark run failed. See logs for details.", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--job-id", 
    required=True, 
    help="ID of the job to check."
)
@click.option(
    "--executor",
    type=click.Choice(["local", "scheduler"]),
    help="Executor used to run the job. If not specified, uses the default from configuration."
)
@click.option(
    "--scheduler-type", 
    default="slurm",
    help="Type of scheduler to use for status check (only for scheduler executor)."
)
def status(job_id: str, executor: Optional[str] = None, scheduler_type: str = "slurm"):
    """Check the status of a submitted job."""
    try:
        # Initialize configuration manager to get default executor
        config_manager = ConfigManager()
        default_config = config_manager.load_default_config()
        default_executor = default_config.get("execution", {}).get("type", "scheduler")
        
        # Use specified executor or default
        executor_type = executor if executor else default_executor
        
        # Create executor instance
        config = {"type": scheduler_type} if executor_type == "scheduler" else {}
        executor_instance = Executor.get_executor(executor_type, config)
        
        # Check job status
        status = executor_instance.check_status(job_id)
        
        click.echo(f"Job {job_id} status: {status}")
        
    except Exception as e:
        click.echo(f"Error checking job status: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--job-id", 
    required=True, 
    help="ID of the job to capture results for."
)
@click.option(
    "--job-name", 
    required=True, 
    help="Name of the job."
)
@click.option(
    "--output-file", 
    multiple=True,
    help="Path to output file to capture. Can be specified multiple times."
)
def capture(job_id: str, job_name: str, output_file: tuple):
    """Capture results for a completed job."""
    try:
        # Initialize result capture
        result_capture = ResultCapture()
        
        # Capture results
        results = result_capture.capture_results(job_id, job_name, list(output_file))
        
        click.echo(f"Results captured for job {job_id} ({job_name})")
        
    except Exception as e:
        click.echo(f"Error capturing results: {e}", err=True)
        sys.exit(1)


@cli.command()
def list_results():
    """List all available results."""
    try:
        # Initialize result capture
        result_capture = ResultCapture()
        
        # Get results list
        results_list = result_capture.list_results()
        
        if results_list:
            click.echo("Available results:")
            for result in results_list:
                click.echo(f"  - Job {result['job_id']} ({result['job_name']}): {result['capture_time']}")
        else:
            click.echo("No results available.")
        
    except Exception as e:
        click.echo(f"Error listing results: {e}", err=True)
        sys.exit(1)


def list_profiles(profile_type: Optional[str] = None):
    """List available profiles."""
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        # Implementation of list_profiles method
    except Exception as e:
        click.echo(f"Error listing profiles: {e}", err=True)
        sys.exit(1)


def show_profile(profile: str):
    """Show the contents of a specific profile."""
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        # Implementation of show_profile method
    except Exception as e:
        click.echo(f"Error showing profile: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli() 