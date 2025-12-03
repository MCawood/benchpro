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
        # Get resolved config and source map
        data, source_map = Config.inspect()
        
        # Flatten the config for display
        flat_items = []
        
        def flatten(node, sources, prefix=""):
            for key, value in node.items():
                current_key = f"{prefix}{key}"
                source = sources.get(key)
                
                if isinstance(value, dict) and isinstance(source, dict):
                    flatten(value, source, f"{current_key}.")
                else:
                    # Format source for brevity
                    source_str = str(source) if source else "unknown"
                    if source_str.startswith(str(Path.home())):
                        source_str = source_str.replace(str(Path.home()), "~")
                    
                    # Truncate very long paths if needed, or just keep them
                    # The user example showed (~/.idevrc), so ~ replacement is good.
                    
                    flat_items.append((current_key, value, source_str))

        flatten(data, source_map)
        
        # Calculate column widths
        if not flat_items:
            console.print("[yellow]Empty configuration[/yellow]")
            return

        max_key_len = max(len(k) for k, _, _ in flat_items)
        max_val_len = max(len(str(v)) for _, v, _ in flat_items)
        
        console.print("[bold]Resolved Configuration:[/bold]")
        
        for key, value, source in flat_items:
            # Format: -> Key : Value (Source)
            # Align key and value
            key_str = f"-> {key}".ljust(max_key_len + 5)
            val_str = str(value).ljust(max_val_len + 2)
            
            console.print(f"[cyan]{key_str}[/cyan] : [green]{val_str}[/green] [dim]({source})[/dim]")
    else:
        # Show user config file content
        config_dir = os.environ.get("BENCHPRO_CONFIG_DIR")
        if config_dir:
            user_config_dir = Path(config_dir)
        else:
            user_config_dir = Path.home() / ".config/benchpro"
            
        config_path = user_config_dir / "config.yaml"
        
        if config_path.exists():
            console.print(f"[bold]User Configuration ({config_path}):[/bold]")
            with open(config_path, "r") as f:
                content = f.read()
            syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            console.print(f"[yellow]No user configuration found at {config_path}[/yellow]")

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
