import click
from rich.console import Console

from benchpro.cli.config import config_cli
from benchpro.cli.suite import suite_cli
from benchpro.cli.results import results_cli
from benchpro.cli.completion import completion_cli
from benchpro.cli.build import build_cli
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
cli.add_command(build_cli, name="build")
cli.add_command(task_cli, name="task")

@cli.command()
def version():
    """Show version info"""
    from benchpro import __version__
    console.print(f"BenchPRO-NG v{__version__}")

if __name__ == "__main__":
    cli()
