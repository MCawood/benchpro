import os
from pathlib import Path
import click
from rich.console import Console
from rich.syntax import Syntax
import yaml

from benchpro.core.config import Config

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

@config_cli.command(name="init")
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
def init_config(force):
    """Initialize user configuration"""
    # Determine config dir
    config_dir = os.environ.get("BENCHPRO_CONFIG_DIR")
    if config_dir:
        user_config_dir = Path(config_dir)
    else:
        user_config_dir = Path.home() / ".config/benchpro"
        
    config_path = user_config_dir / "config.yaml"
    
    if config_path.exists() and not force:
        console.print(f"[yellow]Configuration already exists at {config_path}[/yellow]")
        console.print("Use --force to overwrite")
        return
        
    if force and config_path.exists():
        console.print(f"[yellow]Overwriting configuration at {config_path}[/yellow]")
        
    Config._init_user_config(user_config_dir)
    console.print(f"[green]Initialized configuration in {user_config_dir}[/green]")
