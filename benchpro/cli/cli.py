"""
Command Line Interface for BenchPRO.

This module provides a user-friendly CLI for interacting with BenchPRO,
utilizing the Click library for command-line parsing and execution.
"""

import logging
import os
import sys
import subprocess
from typing import Optional, List, Dict, Any

import click
import yaml

from benchpro.cli.apps import get_app_command
from benchpro.registry.registry_manager import RegistryManager
from benchpro.registry.registry_formatter import RegistryFormatter
from benchpro.utils.logger import get_log_file
from benchpro.cli.completion import get_app_ids, get_profile_names, get_system_names, get_binary_paths
from benchpro.config.config_manager import ConfigManager
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.executor.executor import Executor
from benchpro.results.result_capture import ResultCapture
from benchpro.utils.user_dir import user_dir_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.environ.get("BENCHPRO_DEBUG") != "1" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create CLI group
@click.group()
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--log-level", 
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
              help="Set the logging level for this command execution")
@click.version_option(version="2.0.0", prog_name="BenchPRO")
def cli(debug: bool, log_level: Optional[str] = None):
    """BenchPRO: A tool for building and benchmarking HPC applications."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    elif log_level:
        # Import here to avoid circular imports
        from benchpro.utils.logger import setup_logging
        
        # Convert string log level to int
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        numeric_level = level_map.get(log_level.upper(), logging.INFO)
        
        # Set up logging with this level
        setup_logging(numeric_level)
        logger.debug(f"Logging level set to {log_level}")

# Add the apps command group
cli.add_command(get_app_command)

# Build command
@cli.command()
@click.argument("profile", shell_complete=get_profile_names)
@click.option(
    "--output-dir", 
    help="Directory where build outputs will be stored."
)
@click.option(
    "--system",
    help="System configuration to use",
    shell_complete=get_system_names
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
@click.option(
    "--force",
    is_flag=True,
    help="Force build even if an application with the same name, version, and build parameters already exists."
)
@click.option(
    "--version",
    help="Override the application version specified in the profile."
)
def build(profile: str, output_dir: Optional[str] = None, 
          system: Optional[str] = None, dry_run: bool = False,
          executor: Optional[str] = None, force: bool = False,
          version: Optional[str] = None):
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
        
        # Add force flag to CLI overrides - properly nested to avoid validation errors
        if force:
            cli_overrides["build_parameters"] = {"force": force}
        
        # Add version override if specified
        if version:
            cli_overrides["version"] = version
        
        # Add executor type to CLI overrides if specified, otherwise use default
        if executor:
            cli_overrides["execution"] = {"type": executor}
            # Use the specified executor for output messages
            executor_type = executor
        else:
            # Use the default executor for output messages
            executor_type = default_executor
            
        # Initialize build executor
        task_orchestrator = TaskOrchestrator(config_manager)
        
        # Execute the build
        success, job_id, script_path = task_orchestrator.execute(profile, cli_overrides, dry_run)
        
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
            
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

# Benchmark command
@cli.command()
@click.argument("profile", shell_complete=get_profile_names)
@click.option(
    "--output-dir", 
    help="Directory where benchmark outputs will be stored."
)
@click.option(
    "--system",
    help="System configuration to use",
    shell_complete=get_system_names
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
@click.option(
    "--version",
    help="Override the application version requirement specified in the benchmark profile."
)
def bench(profile: str, output_dir: Optional[str] = None, 
          system: Optional[str] = None, dry_run: bool = False,
          executor: Optional[str] = None, version: Optional[str] = None):
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
        
        # Add version override if specified
        if version:
            if "benchmark" not in cli_overrides:
                cli_overrides["benchmark"] = {}
            if "app_criteria" not in cli_overrides["benchmark"]:
                cli_overrides["benchmark"]["app_criteria"] = {}
            cli_overrides["benchmark"]["app_criteria"]["version"] = version
        
        # Add executor type to CLI overrides if specified, otherwise use default
        if executor:
            cli_overrides["execution"] = {"type": executor}
            # Use the specified executor for output messages
            executor_type = executor
        else:
            # Use the default executor for output messages
            executor_type = default_executor
            
        # Initialize build executor
        task_orchestrator = TaskOrchestrator(config_manager)
        
        # Execute the benchmark
        success, job_id, script_path = task_orchestrator.execute(profile, cli_overrides, dry_run)
        
        if success:
            click.echo(f"Benchmark run script generated: {script_path}")
            
            if dry_run:
                click.echo("Dry run: Job not submitted.")
            else:
                if executor_type == "local":
                    click.echo(f"Benchmark started with PID: {job_id}")
                    # Add information about the capture command
                    click.echo(f"To capture results after completion, use: bp capture --job-id {job_id}")
                else:
                    click.echo(f"Benchmark job submitted with ID: {job_id}")
                    # Add information about the capture command
                    click.echo(f"To capture results after completion, use: bp capture --job-id {job_id}")
        else:
            click.echo("Benchmark run failed. See logs for details.", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

# Status command
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

# Capture command
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
@click.option(
    "--profile",
    help="Name of the benchmark profile to use for result extraction.",
    shell_complete=get_profile_names
)
def capture(job_id: str, job_name: str, output_file: tuple, profile: Optional[str] = None):
    """
    Capture results for a completed job.
    
    If a profile name is provided, extracts metrics from the benchmark output
    using the extraction configuration in the profile.
    """
    try:
        # Initialize result capture
        result_capture = ResultCapture()
        
        # Capture results
        results = result_capture.capture_results(job_id, job_name, list(output_file), profile)
        
        click.echo(f"Results captured for job {job_id} ({job_name})")
        
        # Display extracted metrics if available
        if "extracted_metrics" in results and results["extracted_metrics"]:
            click.echo("\nExtracted Metrics:")
            metric = results["extracted_metrics"]
            click.echo(f"  {metric.get('name', 'value')}: {metric.get('value')} {metric.get('unit', '')}")
        elif profile:
            click.echo("\nNo metrics were extracted. Check the extraction configuration in the profile.")
        
    except Exception as e:
        click.echo(f"Error capturing results: {e}", err=True)
        sys.exit(1)

# List results command
@cli.command()
def list_results():
    """List all available results with extracted metrics."""
    try:
        # Initialize result capture
        result_capture = ResultCapture()
        
        # Get results list
        results_list = result_capture.list_results()
        
        if results_list:
            click.echo("Available results:")
            for result in results_list:
                click.echo(f"  - Job {result['job_id']} ({result['job_name']}): {result['capture_time']}")
                
                # Display metrics if available
                if "extracted_metrics" in result and result["extracted_metrics"]:
                    metric = result["extracted_metrics"]
                    click.echo(f"    Metric: {metric.get('name', 'value')}: {metric.get('value')} {metric.get('unit', '')}")
        else:
            click.echo("No results available.")
        
    except Exception as e:
        click.echo(f"Error listing results: {e}", err=True)
        sys.exit(1)

# Show paths command
@cli.command()
def show_paths():
    """Show the paths to user-specific directories."""
    click.echo("BenchPRO User Directories:")
    click.echo(f"Root: {user_dir_manager.get_path('root')}")
    click.echo(f"Inputs: {user_dir_manager.get_path('inputs')}")
    click.echo(f"Inputs (Application): {user_dir_manager.get_path('inputs_application')}")
    click.echo(f"Inputs (Benchmark): {user_dir_manager.get_path('inputs_benchmark')}")
    click.echo(f"Outputs: {user_dir_manager.get_path('outputs')}")
    click.echo(f"Outputs (Application): {user_dir_manager.get_path('outputs_application')}")
    click.echo(f"Outputs (Benchmark): {user_dir_manager.get_path('outputs_benchmark')}")
    click.echo(f"Registry: {user_dir_manager.get_path('registry')}")
    click.echo(f"Logs: {user_dir_manager.get_path('logs')}")
    click.echo(f"Cache: {user_dir_manager.get_path('cache')}")
    click.echo(f"Applications: {user_dir_manager.get_application_directory()}")
    click.echo(f"Benchmarks: {user_dir_manager.get_benchmark_directory()}")

# Settings command group
@cli.group()
def settings():
    """Manage BenchPRO settings."""
    pass

@settings.command(name="show")
def show_settings():
    """Show current settings."""
    settings = user_dir_manager.load_settings()
    
    click.echo("BenchPRO Settings:")
    for key, value in settings.items():
        click.echo(f"{key}: {value}")

@settings.command(name="set")
@click.option(
    "--application-directory",
    help="Directory for application outputs."
)
@click.option(
    "--benchmark-directory",
    help="Directory for benchmark outputs."
)
@click.option(
    "--logging-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Set the logging level for BenchPRO (DEBUG, INFO, WARNING, ERROR, CRITICAL)."
)
def set_settings(application_directory: Optional[str] = None, benchmark_directory: Optional[str] = None, 
                 logging_level: Optional[str] = None):
    """Update BenchPRO settings."""
    # Load current settings
    settings = user_dir_manager.load_settings()
    
    # Update settings if provided
    if application_directory:
        settings["application_directory"] = application_directory
        click.echo(f"Application directory set to: {application_directory}")
        
    if benchmark_directory:
        settings["benchmark_directory"] = benchmark_directory
        click.echo(f"Benchmark directory set to: {benchmark_directory}")
        
    if logging_level:
        settings["logging_level"] = logging_level
        click.echo(f"Logging level set to: {logging_level}")
        
    # Save settings
    if application_directory or benchmark_directory or logging_level:
        if user_dir_manager.save_settings(settings):
            click.echo("Settings saved successfully.")
        else:
            click.echo("Failed to save settings.", err=True)
    else:
        click.echo("No settings provided. Use --application-directory, --benchmark-directory, or --logging-level to update settings.")

# Shell completion command group
@cli.group()
def completion():
    """Shell completion utilities."""
    pass

@completion.command()
@click.argument("shell", type=click.Choice(["bash", "zsh"]))
def install(shell):
    """Install completion for the specified shell."""
    try:
        if shell == "bash":
            _install_bash_completion()
        elif shell == "zsh":
            _install_zsh_completion()
        else:
            click.echo(f"Shell {shell} is not supported for completion installation.")
    except Exception as e:
        click.echo(f"Error installing completion for {shell}: {e}", err=True)
        sys.exit(1)

def _install_bash_completion():
    """Install bash completion."""
    # Get the user's home directory
    home_dir = os.path.expanduser("~")
    
    # Create the completion script
    script_content = f"""
# BenchPRO bash completion script
_bp_completion() {{
    local IFS=$'\\n'
    local response

    response=$(env _BP_COMPLETE=bash_complete $COMP_LINE)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"
        if [[ $type == 'dir' ]]; then
            COMPREPLY=( $(compgen -d -- "$value") )
        elif [[ $type == 'file' ]]; then
            COMPREPLY=( $(compgen -f -- "$value") )
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done
    return 0
}}

complete -F _bp_completion -o nospace bp
"""
    
    # Write the script to a file
    script_path = os.path.join(home_dir, ".bp_bash_completion.sh")
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Check if the script is already sourced in .bashrc
    bashrc_path = os.path.join(home_dir, ".bashrc")
    source_line = f"source {script_path}"
    
    try:
        with open(bashrc_path, "r") as f:
            bashrc_content = f.read()
        
        if source_line not in bashrc_content:
            # Add the source line to .bashrc
            with open(bashrc_path, "a") as f:
                f.write(f"\n# BenchPRO completion\n{source_line}\n")
    except FileNotFoundError:
        # Create .bashrc if it doesn't exist
        with open(bashrc_path, "w") as f:
            f.write(f"# BenchPRO completion\n{source_line}\n")
    
    click.echo(f"Bash completion script installed at {script_path}")
    click.echo(f"Added source line to {bashrc_path}")
    click.echo("Please restart your shell or run the following command to enable completion:")
    click.echo(f"source {script_path}")

def _install_zsh_completion():
    """Install zsh completion."""
    # Get the user's home directory
    home_dir = os.path.expanduser("~")
    
    # Create the completion directory if it doesn't exist
    zsh_completion_dir = os.path.join(home_dir, ".zsh", "completion")
    os.makedirs(zsh_completion_dir, exist_ok=True)
    
    # Get the completion script directly from Click
    result = subprocess.run(
        ["env", "_BP_COMPLETE=zsh_source", "bp"],
        capture_output=True,
        text=True,
        check=True
    )
    script_content = result.stdout
    
    # Write the script to a file
    script_path = os.path.join(zsh_completion_dir, "_bp")
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Check if the completion directory is in fpath in .zshrc
    zshrc_path = os.path.join(home_dir, ".zshrc")
    fpath_line = f"fpath=({zsh_completion_dir} $fpath)"
    compinit_line = "autoload -U compinit && compinit"
    
    try:
        with open(zshrc_path, "r") as f:
            zshrc_content = f.read()
        
        needs_fpath = fpath_line not in zshrc_content
        needs_compinit = compinit_line not in zshrc_content
        
        if needs_fpath or needs_compinit:
            # Add the necessary lines to .zshrc
            with open(zshrc_path, "a") as f:
                f.write("\n# BenchPRO completion\n")
                if needs_fpath:
                    f.write(f"{fpath_line}\n")
                if needs_compinit:
                    f.write(f"{compinit_line}\n")
    except FileNotFoundError:
        # Create .zshrc if it doesn't exist
        with open(zshrc_path, "w") as f:
            f.write(f"# BenchPRO completion\n{fpath_line}\n{compinit_line}\n")
    
    click.echo(f"Zsh completion script installed at {script_path}")
    click.echo(f"Added completion directory to fpath in {zshrc_path}")
    click.echo("Please restart your shell or run the following commands to enable completion:")
    click.echo(f"{fpath_line}")
    click.echo(f"{compinit_line}")

# Add an initialization command
@cli.command(name="init")
@click.option(
    "--force", 
    is_flag=True, 
    help="Force reinitialization of directories and copy example files."
)
def initialize(force: bool = False):
    """
    Initialize or reinitialize BenchPro directories and example files.
    
    This command ensures all required directories exist and copies example files to the appropriate locations.
    Use the --force flag to recreate directories and copy files even if they already exist.
    """
    try:
        logger.info("Initializing BenchPRO")
        
        # Create directories
        user_dir_manager._ensure_directories()
        logger.info("Directories initialized successfully")
        
        # Copy example files
        success = user_dir_manager.copy_example_profiles()
        if success:
            logger.info("Example profiles copied successfully")
        else:
            logger.warning("Some example profiles could not be copied")
        
        # Show paths to important directories
        click.echo("BenchPRO initialized successfully!")
        click.echo("\nImportant directories:")
        click.echo(f"  Root directory: {user_dir_manager.get_path('root')}")
        click.echo(f"  Application profiles: {user_dir_manager.get_path('inputs_application')}")
        click.echo(f"  Benchmark profiles: {user_dir_manager.get_path('inputs_benchmark')}")
        click.echo(f"  Benchmark outputs: {user_dir_manager.get_path('outputs_benchmark')}")
        click.echo(f"  Application registry: {user_dir_manager.get_path('registry')}")
        click.echo(f"  Log files: {user_dir_manager.get_path('logs')}")
        
        # Additional information
        click.echo("\nNext steps:")
        click.echo("  - Review example profiles in the inputs directories")
        click.echo("  - Build an application: bp build <profile>")
        click.echo("  - Run a benchmark: bp bench <profile>")
        click.echo("  - Capture results: bp capture --job-id <id>")
        
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        click.echo(f"Error during initialization: {str(e)}")
        sys.exit(1)

# Main entry point
def main():
    """Main entry point for the CLI."""
    try:
        # Check if we're running in completion mode
        if "_BP_COMPLETE" in os.environ:
            # We're in completion mode - just run the CLI without extra setup
            cli()
        else:
            # Only perform additional setup when not in completion mode
            # Here you could add any initialization that shouldn't happen during completion
            logger.info("Starting CLI")
            cli()
    except Exception as e:
        log_file = get_log_file()
        error_message = f"Error: {str(e)}"
        if log_file:
            error_message += f"\nSee log file for details: {log_file}"
        click.echo(error_message, err=True)
        if os.environ.get("BP_DEBUG"):
            import traceback
            traceback.print_exc()
        sys.exit(1)

# Import the result capture command
from benchpro.cli.commands.capture import capture_results
cli.add_command(capture_results)

if __name__ == "__main__":
    cli() 