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
@click.option("--all", "show_all", is_flag=True, help="Show all systems (do not filter)")
@click.pass_context
def show_config(ctx, show_all):
    """Show current configuration"""
    from benchpro.core.config import Config, INSTALL_ROOT
    from benchpro.core.utils import abbreviate_path

    # Always resolve
    data, source_map = Config.inspect()
    
    # Filter systems if not --all
    if not show_all and "systems" in data:
        del data["systems"]

    # Prepare extra vars for abbreviation
    extra_vars = {
        "BP_HOME": Config.resolve_user_config_dir(),
        "BP_SITE": INSTALL_ROOT
    }

    # Flatten logic for display
    flat_items = []
    
    def flatten(node, sources, prefix=""):
        for key, value in node.items():
            # Skip keys with None values
            if value is None:
                continue
                
            current_key = f"{prefix}{key}"
            source = sources.get(key)
            
            if isinstance(value, dict) and isinstance(source, dict):
                flatten(value, source, f"{current_key}.")
            else:
                source_str = str(source) if source else "unknown"
                # Use BP vars for source column
                source_disp = abbreviate_path(source_str, extra_vars)
                
                # Abbreviate value if it appears to be a path
                # Use ONLY standard vars for value column (no BP vars)
                val_disp = value
                if isinstance(value, str) and ("/" in value or "\\" in value or value.startswith("$")):
                    val_disp = abbreviate_path(value)
                
                flat_items.append((current_key, val_disp, source_disp))

    flatten(data, source_map)
    
    if not flat_items:
        console.print("[yellow]Empty configuration[/yellow]")
        return

    max_key_len = max(len(k) for k, _, _ in flat_items)
    max_val_len = max(len(str(v)) for _, v, _ in flat_items)
    
    console.print("[bold]Resolved Configuration:[/bold]")
    
    def _matches_schema(key):
        from benchpro.core.config import Config, SystemConfig, BenchProConfig, DefaultsConfig, JobConfig
        from pydantic import BaseModel
        
        parts = key.split(".")
        current = Config
        
        for part in parts:
            if not (isinstance(current, type) and issubclass(current, BaseModel)):
                return False
                
            if part not in current.model_fields:
                return False
                
            # Advance to sub-model if known
            if part == "system": current = SystemConfig
            elif part == "benchpro": current = BenchProConfig
            elif part == "defaults": current = DefaultsConfig
            elif part == "runtime": current = JobConfig
            else: current = None
            
        return True

    for key, value, source in flat_items:
        # Validate key
        is_known = _matches_schema(key)
        if not is_known:
            # Check if source implies validity (Site/Install/Layers)
            # If it comes from $BP_SITE, it's trusted (Site Config, Layers)
            if "$BP_SITE" in source: 
                is_known = True

        if is_known:
            key_color = "cyan"
            val_color = "green"
            src_color = "blue"
        else:
            key_color = "yellow"
            val_color = "yellow"
            src_color = "yellow"
        
        key_str = f"-> {key}".ljust(max_key_len + 5)
        val_str = str(value).ljust(max_val_len + 2)
        console.print(f"[{key_color}]{key_str}[/{key_color}] : [{val_color}]{val_str}[/{val_color}] [{src_color}]({source})[/{src_color}]")

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

def _infer_type(value: str):
    """Infer type from string value."""
    if value.lower() == "true": return True
    if value.lower() == "false": return False
    if value.lower() in ["none", "null"]: return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value

def _update_nested_dict(data, keys, value):
    """Update nested dictionary with value."""
    key = keys[0]
    if len(keys) == 1:
        data[key] = value
        return

    if key not in data or not isinstance(data[key], dict):
        data[key] = {}
        
    _update_nested_dict(data[key], keys[1:], value)

def _delete_nested_key(data, keys):
    """Delete nested key and prune empty parents."""
    key = keys[0]
    if key not in data:
        return False
        
    if len(keys) == 1:
        del data[key]
        return True
        
    if isinstance(data[key], dict):
        result = _delete_nested_key(data[key], keys[1:])
        if result and not data[key]:  # Prune empty dict
            del data[key]
        return result
        
    return False


def _resolve_key_path(target_key: str):
    """Resolve shorthand key to full path (e.g. partition -> system.partition)."""
    if "." in target_key:
        return target_key
        
    from benchpro.core.config import Config, SystemConfig, BenchProConfig, DefaultsConfig, JobConfig
    
    matches = []
    
    # Check top level
    if target_key in Config.model_fields:
        matches.append(target_key)
        
    # Check system
    if target_key in SystemConfig.model_fields:
        matches.append(f"system.{target_key}")
        
    # Check benchpro
    if target_key in BenchProConfig.model_fields:
        matches.append(f"benchpro.{target_key}")
    
    # Check runtime
    if target_key in JobConfig.model_fields:
        matches.append(f"runtime.{target_key}")

    # Check defaults
    if target_key in DefaultsConfig.model_fields:
        matches.append(f"defaults.{target_key}")
        
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        return f"__AMBIGUOUS__:{','.join(matches)}"
        
    return target_key

@config_cli.command(name="set")
@click.argument("settings", nargs=-1, required=True)
def set_config(settings):
    """Set configuration values (e.g. defaults.compiler=gcc)"""
    from benchpro.core.config import Config
    
    for setting in settings:
        if "=" not in setting:
            console.print(f"[yellow]Skipping invalid setting (no '='): {setting}[/yellow]")
            continue
            
        key, value = setting.split("=", 1)
        
        # Use simple type inference here or let core handle it?
        # Core handles boolean/int string conversion slightly differently, 
        # but let's pass strings and let Core infer if implemented, 
        # OR reproduce the inference logic here if Core expects Any.
        # Core's update_user_config has basic inference now (from my previous fix? No, I reverted/modified it).
        # Let's check Core's implementation. 
        # In step 2246 (view) it had:
        # if value.lower() in ["true", "false"]: ...
        # So passing raw string is fine if it matches.
        
        success, msg = Config.update_user_config(key, value)
        if success:
            console.print(f"[green]{msg}[/green]")
        else:
            console.print(f"[red]{msg}[/red]")

@config_cli.command(name="reset")
@click.argument("keys", nargs=-1, required=True)
def reset_config(keys):
    """Reset configuration keys (remove from user config)"""
    from benchpro.core.config import Config
    
    # Resolve user config path
    user_config_dir = Config.resolve_user_config_dir()
    config_path = user_config_dir / "config.yaml"
    
    if not config_path.exists():
        console.print("[yellow]No user configuration file found[/yellow]")
        return
        
    # Load existing config
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        return
        
    changes = []
    
    for key in keys:
        # 1. Try exact match deletion
        if _delete_nested_key(data, key.split(".")):
            changes.append(key)
            continue
            
        # 2. Try Smart Resolution
        resolved_key = _resolve_key_path(key)
        if resolved_key.startswith("__AMBIGUOUS__"):
             matches = resolved_key.split(":", 1)[1]
             console.print(f"[red]Ambiguous key '{key}'. Matches: {matches}[/red]")
             continue

        if resolved_key != key:
             if _delete_nested_key(data, resolved_key.split(".")):
                 console.print(f"[dim]Resolved '{key}' to '{resolved_key}'[/dim]")
                 changes.append(resolved_key)
                 continue
                 
        console.print(f"[yellow]Key not found: {key}[/yellow]")
            
    if changes:
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
            
        for change in changes:
            console.print(f"[green]Reset {change}[/green]")
    else:
        console.print("[yellow]No changes made[/yellow]")
