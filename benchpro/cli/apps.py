"""
Application CLI commands for BenchPRO.

This module provides enhanced CLI commands for managing applications.
"""

import os
import sys
import click
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from tabulate import tabulate

from benchpro.registry.registry_manager import RegistryManager
from benchpro.registry.registry_formatter import RegistryFormatter
from benchpro.cli.completion import get_app_ids, get_app_names, get_app_versions, get_binary_paths


@click.group(name="apps")
def get_app_command():
    """Manage applications in the registry."""
    pass


@get_app_command.command(name="list")
@click.option("--name", help="Filter by application name")
@click.option("--version", help="Filter by application version")
@click.option("--format", "output_format", type=click.Choice(["table", "yaml", "json"]), default="table", 
              help="Output format")
@click.option("--sort", "sort_by", help="Sort by field")
@click.option("--reverse", is_flag=True, help="Reverse sort order")
@click.option("--no-color", is_flag=True, help="Disable color output")
@click.option("--fix", is_flag=True, help="Fix invalid registry entries")
def list_apps(name: Optional[str], version: Optional[str], output_format: str, 
              sort_by: Optional[str], reverse: bool, no_color: bool, fix: bool):
    """List applications in the registry."""
    registry_manager = RegistryManager()
    
    # Load applications from registry
    applications = registry_manager.load().get("applications", [])
    
    # Check for invalid entries
    valid_applications = []
    invalid_entries = []
    for app in applications:
        if isinstance(app, dict):
            valid_applications.append(app)
        else:
            invalid_entries.append(app)
    
    # Fix invalid entries if requested
    if invalid_entries and fix:
        click.echo(f"Found {len(invalid_entries)} invalid entries. Fixing registry...")
        registry_manager.registry["applications"] = valid_applications
        if registry_manager.save():
            click.echo("Registry fixed successfully.")
        else:
            click.echo("Failed to fix registry.")
    elif invalid_entries:
        click.echo(f"Warning: Found {len(invalid_entries)} invalid entries in registry. Use --fix to remove them.")
    
    # Filter applications
    if name:
        valid_applications = [app for app in valid_applications if name.lower() in app.get("name", "").lower()]
    if version:
        valid_applications = [app for app in valid_applications if version.lower() in app.get("version", "").lower()]
    
    # Format output
    formatter = RegistryFormatter(use_colors=not no_color)
    
    if output_format == "table":
        try:
            formatted_output = formatter.format_table(valid_applications, sort_by=sort_by, reverse=reverse)
            click.echo(formatted_output)
        except Exception as e:
            click.echo(f"Error formatting table: {e}", err=True)
            import traceback
            traceback.print_exc()
    elif output_format == "yaml":
        click.echo(formatter.format_yaml(valid_applications))
    elif output_format == "json":
        click.echo(formatter.format_json(valid_applications))


@get_app_command.command(name="info")
@click.argument("app_id", shell_complete=get_app_ids)
@click.option("--no-color", is_flag=True, help="Disable color output")
def app_info(app_id: str, no_color: bool):
    """Get detailed information about an application."""
    registry_manager = RegistryManager()
    applications = registry_manager.load().get("applications", [])
    
    # Filter out invalid entries
    valid_applications = [app for app in applications if isinstance(app, dict)]
    
    # Find application by ID
    app = next((app for app in valid_applications if app.get("id") == app_id), None)
    
    if not app:
        click.echo(f"Application with ID '{app_id}' not found.", err=True)
        sys.exit(1)
    
    # Format output
    formatter = RegistryFormatter(use_colors=not no_color)
    click.echo(formatter.format_application_details(app))


@get_app_command.command(name="remove")
@click.argument("app_id", shell_complete=get_app_ids)
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def remove_app(app_id: str, force: bool):
    """Remove an application from the registry."""
    registry_manager = RegistryManager()
    
    if not force:
        click.confirm(f"Are you sure you want to remove application {app_id}?", abort=True)
    
    success = registry_manager.remove(app_id)
    
    if success:
        click.echo(f"Application {app_id} removed from registry.")
    else:
        click.echo(f"Application {app_id} not found in registry.", err=True)
        sys.exit(1)


@get_app_command.command(name="verify")
@click.argument("app_id", shell_complete=get_app_ids)
@click.option("--no-color", is_flag=True, help="Disable color output")
def verify_app(app_id: str, no_color: bool):
    """Verify the integrity of an application binary."""
    registry_manager = RegistryManager()
    applications = registry_manager.load().get("applications", [])
    
    # Filter out invalid entries
    valid_applications = [app for app in applications if isinstance(app, dict)]
    
    # Find application by ID
    app = next((app for app in valid_applications if app.get("id") == app_id), None)
    
    if not app:
        click.echo(f"Application {app_id} not found in registry.", err=True)
        sys.exit(1)
    
    binary_path = app.get("binary_path", "")
    
    if not binary_path:
        click.echo("No binary path specified for this application.", err=True)
        sys.exit(1)
    
    # Check if binary exists
    if not os.path.exists(binary_path):
        click.echo(f"Binary not found at {binary_path}", err=True)
        sys.exit(1)
    
    # Check if binary is executable
    is_executable = os.access(binary_path, os.X_OK)
    
    # Get file stats
    file_stats = os.stat(binary_path)
    
    # Format output
    click.echo(f"Binary verification for application {app_id}:")
    click.echo(f"  Path: {binary_path}")
    click.echo(f"  Exists: Yes")
    click.echo(f"  Size: {file_stats.st_size} bytes")
    click.echo(f"  Last Modified: {datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    
    if is_executable:
        click.echo(f"  Executable: Yes")
    else:
        click.echo(f"  Executable: No (Warning: Binary is not executable)", err=True)
        sys.exit(1)
    
    click.echo("Verification successful.")


@get_app_command.command(name="stats")
@click.option("--no-color", is_flag=True, help="Disable color output")
def app_stats(no_color: bool):
    """Show statistics about applications in the registry."""
    registry_manager = RegistryManager()
    applications = registry_manager.load().get("applications", [])
    
    # Filter out non-dictionary entries
    valid_applications = []
    invalid_count = 0
    for app in applications:
        if isinstance(app, dict):
            valid_applications.append(app)
        else:
            invalid_count += 1
    
    if not valid_applications:
        click.echo("No valid applications found in registry.")
        if invalid_count > 0:
            click.echo(f"Found {invalid_count} invalid entries. Use 'bp apps list --fix' to fix the registry.")
        return
    
    # Calculate statistics
    total_apps = len(valid_applications)
    status_counts = {}
    for app in valid_applications:
        status = app.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Format output
    formatter = RegistryFormatter(use_colors=not no_color)
    
    click.echo("# Application Registry Statistics")
    click.echo("")
    
    # Basic stats table
    basic_stats = [
        ["Total Applications", str(total_apps)]
    ]
    if invalid_count > 0:
        basic_stats.append(["Invalid Entries", f"{invalid_count} (use 'bp apps list --fix' to fix)"])
    
    click.echo(tabulate(basic_stats, tablefmt="fancy_grid"))
    click.echo("")
    
    # Status breakdown table
    click.echo("# Status Breakdown")
    
    status_table = []
    for status, count in status_counts.items():
        percentage = (count / total_apps) * 100
        status_str = formatter.format_status(status)
        status_table.append([status_str, count, f"{percentage:.1f}%"])
    
    click.echo(tabulate(status_table, headers=["Status", "Count", "Percentage"], tablefmt="fancy_grid"))

    # Show the most recent application
    if valid_applications:
        try:
            # Sort by build timestamp
            sorted_apps = sorted(
                valid_applications, 
                key=lambda x: x.get("build_timestamp", ""), 
                reverse=True
            )
            latest_app = sorted_apps[0]
            name = latest_app.get("name", "unknown")
            version = latest_app.get("version", "unknown")
            timestamp = latest_app.get("build_timestamp", "unknown")
            
            if timestamp != "unknown":
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    pass
            
            click.echo("")
            click.echo("# Most Recent Application")
            
            latest_info = [
                ["Name", name],
                ["Version", version],
                ["Build Time", timestamp]
            ]
            
            click.echo(tabulate(latest_info, tablefmt="fancy_grid"))
            
        except Exception as e:
            click.echo(f"Error displaying most recent application: {e}", err=True)


@get_app_command.command(name="clean")
@click.option("--force", is_flag=True, help="Force cleaning without confirmation")
def clean_registry(force: bool):
    """Clean the registry by removing entries with missing binaries."""
    registry_manager = RegistryManager()
    applications = registry_manager.load().get("applications", [])
    
    # Filter out invalid entries
    valid_applications = [app for app in applications if isinstance(app, dict)]
    
    # Find applications with missing binaries
    to_remove = []
    for app in valid_applications:
        binary_path = app.get("binary_path", "")
        if binary_path and not os.path.exists(binary_path):
            to_remove.append(app)
    
    if not to_remove:
        click.echo("No applications with missing binaries found.")
        return
    
    click.echo(f"Found {len(to_remove)} applications with missing binaries:")
    for app in to_remove:
        click.echo(f"  {app.get('id')}: {app.get('name')} {app.get('version')}")
    
    if not force:
        click.confirm("Do you want to remove these applications from the registry?", abort=True)
    
    # Remove applications
    for app in to_remove:
        registry_manager.remove(app.get("id"))
    
    click.echo(f"Removed {len(to_remove)} applications from the registry.")


@get_app_command.command(name="register")
@click.argument("app_name")
@click.argument("binary_path", shell_complete=get_binary_paths)
@click.option("--version", default="1.0", help="Application version")
@click.option("--description", help="Application description")
@click.option("--compiler", help="Compiler used to build the application")
@click.option("--flags", help="Compiler flags used to build the application")
def register_app(app_name: str, binary_path: str, version: str = "1.0", 
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