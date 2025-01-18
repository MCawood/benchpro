"""
BenchPRO Command Line Interface.

This module provides the command-line interface for BenchPRO,
allowing users to create and manage builds and benchmarks.
"""

import click
from pathlib import Path
from .build import build  # Import the build command group
from .settings import settings  # Import the settings command group

@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    """BenchPRO - A benchmark execution and management tool.
    
    Shell completion installation:
    
    \b
    # Bash
    echo 'eval "$(_BP_COMPLETE=bash_source bp)"' >> ~/.bashrc
    
    \b
    # Zsh
    echo 'eval "$(_BP_COMPLETE=zsh_source bp)"' >> ~/.zshrc
    
    \b
    # Fish
    echo 'eval (env _BP_COMPLETE=fish_source bp)' >> ~/.config/fish/config.fish
    """
    # Initialize context object if not already done
    ctx.ensure_object(dict)

cli.add_command(build)  # Add the build command group
cli.add_command(settings)  # Add the settings command group

@cli.command()
@click.option('--testing', is_flag=True, help='Initialize in testing mode')
@click.option('--force', is_flag=True, help='Force reinitialization')
def init(testing: bool, force: bool):
    """Initialize a BenchPRO workspace."""
    try:
        # Determine workspace directory
        if testing:
            workspace = Path.cwd() / 'testing' / 'benchpro'
        else:
            workspace = Path.cwd() / '.benchpro'

        # Check if workspace exists
        if workspace.exists() and not force:
            click.echo("Workspace already exists. Use --force to reinitialize.")
            return

        # Remove existing workspace if force flag is set
        if workspace.exists() and force:
            import shutil
            shutil.rmtree(workspace)

        # Create directory structure
        workspace.mkdir(parents=True, exist_ok=True)
        for dir_name in ['tasks', 'jobs', 'templates', 'applications', 'cache', 'logs']:
            (workspace / dir_name).mkdir(exist_ok=True)

        # Create config file
        config = {
            'workspace': {
                'root': str(workspace),
                'testing': testing
            }
        }
        config_file = workspace / 'config.yaml'
        import yaml
        with config_file.open('w') as f:
            yaml.safe_dump(config, f)

        click.echo(f"Initialized BenchPRO workspace in {workspace}")

    except Exception as e:
        raise click.ClickException(str(e)) 