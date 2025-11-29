import click
from rich.console import Console
from rich.syntax import Syntax
import yaml

console = Console()

@click.group()
def config_cli():
    """Manage configuration"""
    pass

@config_cli.command(name="show")
@click.option("--resolved", is_flag=True, help="Show fully resolved config")
@click.pass_context
def show_config(ctx, resolved):
    """Show current configuration"""
    config = ctx.obj['config']
    
    if resolved:
        # Dump the pydantic model to dict then yaml
        data = config.model_dump()
        yaml_str = yaml.dump(data, sort_keys=False)
        syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print("[yellow]Use --resolved to see the full merged config[/yellow]")
