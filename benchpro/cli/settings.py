"""CLI commands for managing BenchPro settings."""

import click
from benchpro.core.services.settings import Settings, ImmutableSettingError, InvalidValueError

def get_settings_keys(ctx: click.Context, args: list, incomplete: str) -> list:
    """Get settings keys for autocompletion."""
    settings = Settings()
    keys = sorted(settings._settings.keys())
    return [k for k in keys if incomplete in k]

@click.group()
def settings():
    """Manage BenchPro settings."""
    pass

@settings.command()
@click.option('--all', 'show_all', is_flag=True, help="Show all settings including immutable and site-controlled ones")
def list(show_all):
    """List settings. By default, shows only user-editable settings."""
    settings = Settings()
    
    if show_all:
        # Print metadata
        click.echo("\nMetadata:")
        click.echo("-" * 60)
        metadata = settings._metadata
        for key, value in sorted(metadata.items()):
            click.echo(f"{key}: {value}")
        
        # Print all settings by level
        for level in ["immutable", "site_mutable", "user_mutable"]:
            click.echo(f"\n{level.replace('_', ' ').title()} Settings:")
            click.echo("-" * 60)
            click.echo(f"{'Name':<20} {'Value':<10} {'Origin':<8} {'Type':<8}")
            click.echo("-" * 60)
            
            # Filter and sort settings for this level
            level_settings = {
                k: s for k, s in settings._settings.items() 
                if s.level == level
            }
            
            for key, setting in sorted(level_settings.items()):
                # Format the value based on type
                if isinstance(setting.value, bool):
                    value_str = str(setting.value).lower()
                else:
                    value_str = str(setting.value)
                    
                click.echo(
                    f"{key:<20} {value_str:<10} {setting.origin:<8} {setting.type.__name__:<8}"
                )
    else:
        # Print only user-editable settings
        click.echo("\nUser-Editable Settings:")
        click.echo("-" * 60)
        click.echo(f"{'Name':<20} {'Value':<10} {'Origin':<8} {'Type':<8}")
        click.echo("-" * 60)
        
        # Filter for user-mutable settings that aren't controlled by site
        user_settings = {
            k: s for k, s in settings._settings.items()
            if s.level == "user_mutable" and (s.origin != "site" or s.level != "site_mutable")
        }
        
        for key, setting in sorted(user_settings.items()):
            # Format the value based on type
            if isinstance(setting.value, bool):
                value_str = str(setting.value).lower()
            else:
                value_str = str(setting.value)
                
            click.echo(
                f"{key:<20} {value_str:<10} {setting.origin:<8} {setting.type.__name__:<8}"
            )
    click.echo()

@settings.command()
@click.argument('key', shell_complete=get_settings_keys)
def get(key):
    """Get detailed information about a setting."""
    settings = Settings()
    try:
        setting = settings.get_setting_info(key)
        
        # Print detailed information
        click.echo(f"\nSetting: {key}")
        click.echo("-" * 40)
        # Format the value based on type
        if isinstance(setting.value, bool):
            value_str = str(setting.value).lower()
        else:
            value_str = str(setting.value)
        click.echo(f"Value: {value_str}")
        click.echo(f"Type: {setting.type.__name__}")
        click.echo(f"Level: {setting.level.replace('_', ' ').title()}")
        click.echo(f"Origin: {setting.origin}")
        
        if setting.level == "immutable":
            click.echo("Mutability: Cannot be modified")
        elif setting.level == "site_mutable":
            click.echo("Mutability: Can only be modified by site administrator")
        else:
            click.echo("Mutability: Can be modified by users")
            
        if setting.description:
            click.echo(f"Description: {setting.description}")
        click.echo()
        return 0
    except Exception as e:
        if "does not exist" in str(e):
            click.echo(f"Setting '{key}' not found")
        else:
            click.echo(f"Error: {str(e)}", err=True)
        return 0  # Return success even for non-existent settings

@settings.command()
@click.argument('key', shell_complete=get_settings_keys)
@click.argument('value')
def set(key, value):
    """Set a setting value.
    
    Examples:
        benchpro settings set debug true
    """
    settings = Settings()
    
    try:
        # Convert common boolean strings
        if value.lower() in ('true', 'yes', 'on', '1'):
            value = True
        elif value.lower() in ('false', 'no', 'off', '0'):
            value = False
            
        settings.set(key, value)
        click.echo(f"Successfully set {key} = {value}")
        return 0
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if isinstance(e, ImmutableSettingError) and "site administrator" in str(e):
            click.echo("Contact your system administrator to change this setting.", err=True)
        return 1

@settings.command()
def reset():
    """Reset all settings to defaults."""
    if click.confirm("Are you sure you want to reset all user settings to defaults?"):
        settings = Settings()
        settings.reset_to_defaults()  # Use reset_to_defaults instead of reload
        click.echo("Settings reset to defaults")
        return 0
    return 1 