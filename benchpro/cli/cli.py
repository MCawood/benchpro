"""
Command Line Interface for BenchPRO.

This module provides a user-friendly CLI using Click.
"""

import os
import sys
import click
import logging
import yaml
import warnings
import subprocess
from typing import Dict, Any, Optional, List

from benchpro import __version__
from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.task_factory import TaskFactory
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.executor.executor import Executor
from benchpro.results.result_capture import ResultCapture
from benchpro.registry.registry_manager import RegistryManager
from benchpro.utils.user_dir import user_dir_manager
from benchpro.utils.logger import get_logger, get_log_file, setup_logging
from benchpro.cli.completion import (
    get_profile_names,
    get_system_names,
    get_app_names,
    get_app_versions,
    get_app_ids,
    get_binary_paths
)

# Only configure logging if we're not in completion mode
if "_BP_COMPLETE" not in os.environ:
    # Configure logging
    setup_logging()
    logger = get_logger(__name__)
else:
    # Disable logging and warnings in completion mode
    import logging
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    # Create a null logger
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
    
    # Suppress Pydantic warnings
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


@click.group()
@click.version_option(version=__version__)
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, debug):
    """BenchPro CLI."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


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


@cli.group()
def registry():
    """Manage the application registry."""
    pass


@registry.command(name="list")
@click.option(
    "--name",
    help="Filter applications by name.",
    shell_complete=get_app_names
)
@click.option(
    "--version",
    help="Filter applications by version.",
    shell_complete=get_app_versions
)
@click.option(
    "--format",
    type=click.Choice(["table", "yaml", "json"]),
    default="table",
    help="Output format."
)
def list_registry(name: Optional[str] = None, version: Optional[str] = None, format: str = "table"):
    """List applications in the registry."""
    registry_manager = RegistryManager()
    registry_manager.load()
    
    # Apply filters
    criteria = {}
    if name:
        criteria["name"] = name
    if version:
        criteria["version"] = version
        
    if criteria:
        applications = registry_manager.find_applications(criteria)
    else:
        applications = registry_manager.list_applications()
    
    if not applications:
        click.echo("No applications found in registry.")
        return
    
    if format == "yaml":
        click.echo(yaml.dump({"applications": applications}, default_flow_style=False))
    elif format == "json":
        import json
        click.echo(json.dumps({"applications": applications}, indent=2))
    else:  # table format
        # Determine the maximum length of each field for better formatting
        max_id_len = max([len(app.get("id", "")) for app in applications] + [2])
        max_name_len = max([len(app.get("name", "")) for app in applications] + [4])
        max_version_len = max([len(str(app.get("version", ""))) for app in applications] + [7])
        
        # Ensure minimum column widths
        id_width = max(max_id_len, 25)
        name_width = max(max_name_len, 15)
        version_width = max(max_version_len, 10)
        status_width = 10
        binary_width = 50
        
        # Print header
        header = f"{'ID':<{id_width}} {'Name':<{name_width}} {'Version':<{version_width}} {'Status':<{status_width}} {'Binary Path':<{binary_width}}"
        click.echo(header)
        click.echo("-" * (id_width + name_width + version_width + status_width + binary_width + 4))
        
        # Print each application
        for app in applications:
            app_id = app.get("id", "")
            name = app.get("name", "")
            version = str(app.get("version", ""))
            status = app.get("status", "")
            binary_path = app.get("binary_path", "")
            
            # Only truncate binary path if necessary
            if len(binary_path) > binary_width:
                binary_path = "..." + binary_path[-(binary_width-3):]
                
            row = f"{app_id:<{id_width}} {name:<{name_width}} {version:<{version_width}} {status:<{status_width}} {binary_path:<{binary_width}}"
            click.echo(row)


@registry.command()
@click.argument("app_id", shell_complete=get_app_ids)
def info(app_id: str):
    """Show detailed information about an application."""
    registry_manager = RegistryManager()
    app = registry_manager.find_application(app_id)
    
    if not app:
        click.echo(f"Application with ID {app_id} not found.")
        return
    
    click.echo(yaml.dump(app, default_flow_style=False))


@registry.command()
@click.argument("app_id", shell_complete=get_app_ids)
@click.option(
    "--force",
    is_flag=True,
    help="Force removal even if binary exists."
)
def remove(app_id: str, force: bool = False):
    """Remove an application from the registry."""
    registry_manager = RegistryManager()
    app = registry_manager.find_application(app_id)
    
    if not app:
        click.echo(f"Application with ID {app_id} not found.")
        return
    
    # Check if the binary exists
    binary_path = app.get("binary_path", "")
    if os.path.exists(binary_path) and not force:
        click.echo(f"Binary still exists at {binary_path}. Use --force to remove anyway.")
        return
    
    # Remove the application
    if registry_manager.remove_application(app_id):
        click.echo(f"Removed application {app.get('name', '')} with ID {app_id}.")
    else:
        click.echo(f"Failed to remove application with ID {app_id}.")


@registry.command("clean")
@click.option("--force", is_flag=True, help="Force cleanup without confirmation")
def registry_clean(force):
    """Clean the registry by removing entries with non-existent binary paths."""
    try:
        registry_manager = RegistryManager()
        
        # Get all applications
        applications = registry_manager.list_applications()
        
        # Filter applications with non-existent binary paths
        invalid_apps = []
        for app in applications:
            binary_path = app.get("binary_path", "")
            if not os.path.exists(binary_path):
                invalid_apps.append(app)
        
        if not invalid_apps:
            click.echo("No invalid applications found in the registry.")
            return
        
        # Display applications to be removed
        click.echo(f"Found {len(invalid_apps)} applications with non-existent binary paths:")
        for app in invalid_apps:
            click.echo(f"  - {app.get('name')} {app.get('version')} (ID: {app.get('id')})")
            click.echo(f"    Binary path: {app.get('binary_path')}")
        
        # Confirm removal
        if not force and not click.confirm("Do you want to remove these applications from the registry?"):
            click.echo("Cleanup cancelled.")
            return
        
        # Remove applications
        for app in invalid_apps:
            registry_manager.remove_application(app.get("id"))
        
        # Save the registry
        registry_manager.save()
        
        click.echo(f"Successfully removed {len(invalid_apps)} applications from the registry.")
    except Exception as e:
        click.echo(f"Error cleaning registry: {e}", err=True)
        sys.exit(1)


@registry.command()
@click.argument("app_name", shell_complete=get_app_names)
@click.argument("binary_path", shell_complete=get_binary_paths)
@click.option(
    "--version",
    default="1.0",
    help="Application version."
)
@click.option(
    "--description",
    help="Application description."
)
@click.option(
    "--compiler",
    help="Compiler used to build the application."
)
@click.option(
    "--flags",
    help="Compiler flags used to build the application."
)
def register(app_name: str, binary_path: str, version: str = "1.0", 
             description: Optional[str] = None, compiler: Optional[str] = None,
             flags: Optional[str] = None):
    """Manually register an application in the registry."""
    # Check if the binary exists
    if not os.path.exists(binary_path):
        click.echo(f"Binary not found at {binary_path}.")
        return
    
    # Get absolute path to the binary
    binary_path = os.path.abspath(binary_path)
    
    # Prepare application data
    app_data = {
        "name": app_name,
        "version": version,
        "workspace_dir": os.path.dirname(binary_path),
        "binary_path": binary_path,
        "build_parameters": {
            "compiler": compiler or "unknown",
            "flags": flags or ""
        },
        "metadata": {
            "description": description or "",
            "tags": []
        }
    }
    
    # Register the application
    registry_manager = RegistryManager()
    app_id = registry_manager.register_application(app_data)
    
    if app_id:
        click.echo(f"Registered application {app_name} with ID: {app_id}")
    else:
        click.echo("Failed to register application.")


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
def set_settings(application_directory: Optional[str] = None, benchmark_directory: Optional[str] = None):
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
        
    # Save settings
    if application_directory or benchmark_directory:
        if user_dir_manager.save_settings(settings):
            click.echo("Settings saved successfully.")
        else:
            click.echo("Failed to save settings.", err=True)
    else:
        click.echo("No settings provided. Use --application-directory or --benchmark-directory to update settings.")


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


def main():
    """Entry point for the CLI."""
    # Check if we're running in completion mode
    if "_BP_COMPLETE" in os.environ:
        # We're in completion mode - just run the CLI
        cli()
    else:
        # Only initialize user directory if not in completion mode
        if not user_dir_manager.is_initialized():
            user_dir_manager.ensure_file_directory(user_dir_manager.get_path("root"))
            logger.info("Initializing user directory")
        
        logger.info("Starting CLI")
        cli()


# Add this block to ensure main() is called when the module is run directly
if __name__ == "__main__":
    main() 