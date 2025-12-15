import click
import sys
from pathlib import Path
from rich.console import Console

from benchpro.cli.config import config_cli
from benchpro.cli.bench import bench_cli
from benchpro.cli.completion import completion_cli
from benchpro.cli.build import app_cli
from benchpro.cli.result import result_cli
from benchpro.core.config import Config

from benchpro.core.logger import setup_logging, get_logger
from benchpro.core.exceptions import BenchProError

# Initialize logger (will be configured in cli)
logger = get_logger()
console = Console(stderr=True)

def handle_exception(func):
    """Decorator to handle exceptions globally."""
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Disable click's standalone mode so exceptions bubble up to us
            return func(standalone_mode=False, *args, **kwargs)
        except BenchProError as e:
            logger.error(f"{e.message}")
            sys.exit(e.exit_code)
        except click.exceptions.Exit as e:
            # Allow click to exit normally (e.g. --help or successful completion)
            sys.exit(e.exit_code)
        except click.exceptions.Abort:
            # Handle aborts (Ctrl+C)
            logger.error("Aborted")
            sys.exit(1)
        except click.ClickException as e:
            # Handle click exceptions (usage errors, etc)
            e.show()
            sys.exit(e.exit_code)
        except Exception as e:
            logger.exception("An unexpected error occurred")
            console.print(f"[red]CRITICAL ERROR: {e}[/red]")
            console.print("Please report this bug to the developers.")
            sys.exit(1)
    return wrapper

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, debug):
    """BenchPRO-NG: HPC Benchmark Orchestrator"""
    ctx.ensure_object(dict)
    
    # Setup logging
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level)
    
    if debug:
        logger.debug("Debug mode enabled")
    
    # Load config globally
    try:
        ctx.obj['config'] = Config.load()
    except Exception as e:
        # We'll let the command handlers deal with config errors if needed, 
        # or we could wrap this too. For now, just log and exit.
        # But wait, we can't use the decorator on the group easily for this part.
        # Let's just use try/except here with the new pattern.
        logger.error(f"Error loading config: {e}")
        ctx.exit(1)

# Register subcommands
cli.add_command(config_cli, name="config")
cli.add_command(bench_cli, name="bench")
cli.add_command(completion_cli, name="completion")
cli.add_command(app_cli, name="app")
cli.add_command(result_cli)

# Setup run shortcut
from benchpro.cli.bench import run_bench
# We can't easily re-use the command decorated by another group without some hacks.
# But we can verify with `bench run`.
# I will NOT add `run` to toplevel right now to avoid complexity.
# Just ensuring imports are correct.


@cli.command()
@click.option("--force", is_flag=True, help="Force re-initialization of user configuration")
def init(force):
    """Initialize BenchPRO environment"""
    import os
    from benchpro.core.results import ResultStore
    from benchpro.core.config import Config, CONFIG_FILENAME
    
    # 1. Initialize User Config
    user_config_dir = Config.resolve_user_config_dir()
    config_path = user_config_dir / CONFIG_FILENAME
    
    if force and config_path.exists():
        logger.warning(f"Overwriting user configuration at {config_path}")
        try:
            config_path.unlink()
        except Exception as e:
            logger.error(f"Failed to remove existing config: {e}")
            return

    if not config_path.exists():
        try:
            Config._init_user_config(user_config_dir)
            logger.info(f"Initialized user configuration at {user_config_dir}")
        except Exception as e:
            logger.error(f"Failed to create configuration: {e}")
            return
    else:
        logger.info(f"User configuration found at {user_config_dir}")

    # 2. Load Config to detect workspace and ensure it exists
    try:
        config = Config.load()
        if config.system.workspace_dir:
             workspace_path = Path(os.path.expandvars(config.system.workspace_dir)).expanduser()
             if not workspace_path.exists():
                 workspace_path.mkdir(parents=True, exist_ok=True)
                 logger.info(f"Created workspace directory at {workspace_path}")
             else:
                 logger.info(f"Verified workspace at {workspace_path}")
    except Exception as e:
        logger.warning(f"Could not verify workspace: {e}")

    # 3. Initialize Database
    try:
        store = ResultStore()
        logger.info(f"Initialized database at {store.db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
        
    console.print(f"\n[bold green]✓ BenchPRO initialized successfully![/bold green]")
    console.print(f"Configuration: {config_path}")
    if 'store' in locals():
         console.print(f"Database:      {store.db_path}")

@cli.command()
@click.option("--shell", default="bash", type=click.Choice(["bash", "zsh", "fish"]), help="Target shell language")
def env(shell):
    """Output environment variables for shell integration."""
    from benchpro.core.config import Config, INSTALL_ROOT
    
    # Resolve BP_HOME (User Config Dir)
    bp_home = Config.resolve_user_config_dir()
    
    # Resolve BP_SITE (Installation Root)
    bp_site = INSTALL_ROOT
    
    # Define exports
    exports = {
        "BP_HOME": str(bp_home),
        "BP_SITE": str(bp_site)
    }
    
    # Format output based on shell
    for var, val in exports.items():
        if shell == "fish":
            print(f"set -x {var} \"{val}\"")
        else:
            print(f"export {var}=\"{val}\"")

@cli.command()
def version():
    """Show version info"""
    from benchpro import __version__
    console.print(f"BenchPRO-NG v{__version__}") # Keep console.print for simple output like version

# Wrap the CLI entry point to handle exceptions
# This ensures that when installed as an entry point, exceptions are handled
cli = handle_exception(cli)

if __name__ == "__main__":
    cli()
