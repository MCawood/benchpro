import click
import sys
from pathlib import Path
from rich.console import Console

from benchpro.cli.config import config_cli
from benchpro.cli.bench import bench_cli
from benchpro.cli.completion import completion_cli
from benchpro.cli.build import app_cli
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

cli.add_command(config_cli, name="config")
cli.add_command(bench_cli, name="bench")
cli.add_command(completion_cli, name="completion")
cli.add_command(app_cli, name="app")

@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing project configuration")
def init(force):
    """Initialize a BenchPRO project workspace in the current directory"""
    from benchpro.core.results import ResultStore
    from benchpro.core.config import Config
    
    project_dir = Path.cwd()
    benchpro_dir = project_dir / ".benchpro"
    config_path = benchpro_dir / "config.yaml"
    profiles_dir = benchpro_dir / "profiles"
    
    # Check if already initialized
    if benchpro_dir.exists() and not force:
        logger.warning(f"Project already initialized at {benchpro_dir}")
        logger.info("Use --force to reinitialize")
        return
    
    if force and benchpro_dir.exists():
        logger.warning(f"Reinitializing project at {benchpro_dir}")
    
    # Create project directory structure
    benchpro_dir.mkdir(exist_ok=True)
    profiles_dir.mkdir(exist_ok=True)
    
    # Initialize user config if needed (this also creates ~/.config/benchpro)
    user_config_dir = Path.home() / ".config/benchpro"
    if not (user_config_dir / "config.yaml").exists():
        Config._init_user_config(user_config_dir)
        logger.info("Initialized user configuration")
    
    # Initialize database (ensures schema is up to date)
    try:
        store = ResultStore()
        logger.info(f"Initialized database at {store.db_path}")
    except Exception as e:
        logger.warning(f"Failed to initialize database: {e}")
    
    # Create project config if it doesn't exist
    if not config_path.exists() or force:
        with open(config_path, "w") as f:
            import yaml
            yaml.dump({
                "defaults": {
                    "root_dir": str(project_dir / "benchpro")
                }
            }, f)
        logger.info(f"Created project config at {config_path}")
    
    console.print(f"\n[bold green]✓ Project initialized successfully![/bold green]")
    console.print(f"\nProject directory: {benchpro_dir}")
    console.print(f"Profiles directory: {profiles_dir}")
    console.print(f"\nNext steps:")
    console.print(f"  • Add application profiles to {profiles_dir}")
    console.print(f"  • Run 'bp app avail' to see available applications")
    console.print(f"  • Run 'bp app build <app>' to build an application")

@cli.command()
def version():
    """Show version info"""
    from benchpro import __version__
    console.print(f"BenchPRO-NG v{__version__}") # Keep console.print for simple output like version

# Wrap the CLI entry point to handle exceptions
cli = handle_exception(cli)

if __name__ == "__main__":
    cli()
