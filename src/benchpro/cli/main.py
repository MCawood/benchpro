import click
from pathlib import Path
from rich.console import Console

from benchpro.cli.config import config_cli
from benchpro.cli.suite import suite_cli
from benchpro.cli.results import results_cli
from benchpro.cli.completion import completion_cli
from benchpro.cli.build import app_cli
from benchpro.cli.task import task_cli
from benchpro.core.config import Config

console = Console()

@click.group()
@click.pass_context
def cli(ctx):
    """BenchPRO-NG: HPC Benchmark Orchestrator"""
    ctx.ensure_object(dict)
    # Load config globally
    try:
        ctx.obj['config'] = Config.load()
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        ctx.exit(1)

cli.add_command(config_cli, name="config")
cli.add_command(suite_cli, name="suite")
cli.add_command(results_cli, name="results")
cli.add_command(completion_cli, name="completion")
cli.add_command(app_cli, name="app")
cli.add_command(task_cli, name="task")

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
        console.print(f"[yellow]Project already initialized at {benchpro_dir}[/yellow]")
        console.print("Use --force to reinitialize")
        return
    
    if force and benchpro_dir.exists():
        console.print(f"[yellow]Reinitializing project at {benchpro_dir}[/yellow]")
    
    # Create project directory structure
    benchpro_dir.mkdir(exist_ok=True)
    profiles_dir.mkdir(exist_ok=True)
    
    # Initialize user config if needed (this also creates ~/.config/benchpro)
    user_config_dir = Path.home() / ".config/benchpro"
    if not (user_config_dir / "config.yaml").exists():
        Config._init_user_config(user_config_dir)
        console.print(f"[green]Initialized user configuration[/green]")
    
    # Initialize database (ensures schema is up to date)
    try:
        store = ResultStore()
        console.print(f"[green]Initialized database at {store.db_path}[/green]")
    except Exception as e:
        console.print(f"[red]Warning: Failed to initialize database: {e}[/red]")
    
    # Create project config if it doesn't exist
    if not config_path.exists() or force:
        with open(config_path, "w") as f:
            import yaml
            yaml.dump({
                "defaults": {
                    "root_dir": str(project_dir / "benchpro")
                }
            }, f)
        console.print(f"[green]Created project config at {config_path}[/green]")
    
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
    console.print(f"BenchPRO-NG v{__version__}")

if __name__ == "__main__":
    cli()
