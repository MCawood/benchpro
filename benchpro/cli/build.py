"""Build command for BenchPRO CLI."""

import asyncio
import click
from click.shell_completion import CompletionItem
from pathlib import Path
from typing import Optional, Tuple, List

from benchpro.core.domain.templates.loader import TemplateLoader
from benchpro.core.infrastructure.local_executor import LocalExecutor
from benchpro.core.services.build_orchestrator import BuildOrchestrator
from benchpro.core.services.logging import setup_logging, get_logger
from benchpro.core.services.settings import Settings
from benchpro.core.services.location_manager import LocationManager
from benchpro.core.domain.task_registry import TaskRegistry

logger = get_logger("build")

def parse_variables(var_tuples: Tuple[str, ...]) -> dict:
    """Parse variable tuples into a dictionary.
    
    Args:
        var_tuples: Tuple of strings in KEY=VALUE format
        
    Returns:
        Dictionary of variables
    """
    variables = {}
    for var in var_tuples:
        try:
            key, value = var.split('=', 1)
            variables[key.strip()] = value.strip()
        except ValueError:
            raise click.BadParameter(f"Invalid variable format: {var}. Use KEY=VALUE format.")
    return variables

def list_available_templates(template_loader: TemplateLoader) -> None:
    """List available application templates.
    
    Args:
        template_loader: Template loader instance
    """
    templates = template_loader.list_applications()
    if not templates:
        click.echo("No application templates found.")
        return
        
    click.echo("\nAvailable application templates:")
    for template in sorted(templates):
        click.echo(f"  - {template}")
    click.echo()

def get_template_names(ctx: click.Context, args: List[str], incomplete: str) -> List[CompletionItem]:
    """Get template names for shell completion.
    
    Args:
        ctx: Click context
        args: Command arguments
        incomplete: Current incomplete argument
        
    Returns:
        List of completion items
    """
    try:
        root_path = Path.cwd()
        template_path = root_path / "templates"  # Root template directory
        template_loader = TemplateLoader(template_path)  # TemplateLoader will handle applications subdirectory
        
        templates = []
        for name in template_loader.list_applications():
            if incomplete and not name.startswith(incomplete):
                continue
            try:
                config = template_loader.load_config(name)
                description = config.description.split('\n')[0] if config.description else "No description"
                templates.append(CompletionItem(name, help=description))
            except Exception:
                templates.append(CompletionItem(name, help="[Error loading configuration]"))
        
        return templates
    except Exception:
        return []  # Return empty list if template directory doesn't exist or other errors

@click.command()
@click.argument('name', required=False, shell_complete=get_template_names)
@click.option('--avail', is_flag=True, help='List available application templates')
@click.option('--var', '-v', multiple=True, help='Variables in KEY=VALUE format')
@click.option('--template-dir', type=click.Path(), help='Template directory')
@click.option('--root-dir', type=click.Path(), help='BenchPRO root directory')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def build(name: Optional[str], avail: bool, var: tuple, template_dir: str, root_dir: str, debug: bool):
    """Build an application from a template."""
    # Set up logging
    settings = Settings()
    debug = debug or settings.get("debug", False)
    log_dir = Path(root_dir or Path.cwd()) / "logs"
    setup_logging(debug=debug, log_dir=log_dir)
    
    async def _build():
        try:
            # Initialize paths
            root_path = Path(root_dir) if root_dir else Path.cwd()
            template_path = Path(template_dir) if template_dir else root_path / "templates"
            
            logger.debug("Initializing with paths: root=%s, templates=%s", root_path, template_path)
            template_loader = TemplateLoader(template_path)
            
            # Handle --avail flag
            if avail:
                list_available_templates(template_loader)
                return
                
            # Require name argument if not listing templates
            if not name:
                logger.error("No template name provided")
                raise click.UsageError("Missing argument 'NAME'. Specify a template name or use --avail to list available templates.")
            
            # Parse variables
            try:
                variables = parse_variables(var)
                if variables:
                    logger.debug("Template variables: %s", variables)
            except click.BadParameter as e:
                logger.error("Invalid variable format: %s", str(e))
                raise
            
            # Initialize services
            logger.debug("Initializing build services")
            executor = LocalExecutor()
            location_manager = LocationManager(settings)
            task_registry = TaskRegistry()
            
            orchestrator = BuildOrchestrator(
                template_loader=template_loader,
                executor=executor,
                location_manager=location_manager,
                task_registry=task_registry,
                root_dir=root_path
            )
            
            logger.info("Building application: %s", name)
            if variables:
                logger.info("Variables:")
                for key, value in variables.items():
                    logger.info("  %s: %s", key, value)
            
            # Run build
            try:
                app_dir = await orchestrator.build_application(name, variables)
                
                logger.info("Successfully built %s", name)
                logger.info("Application installed to: %s", app_dir)
                logger.info("Build artifacts in: %s", app_dir/'build')
                logger.info("Source files in: %s", app_dir/'source')
                logger.info("Installation files in: %s", app_dir/'install')
                
                # Echo success messages to console for user feedback
                click.echo(f"Successfully built {name}")
                click.echo(f"Application installed to: {app_dir}")
                
            except Exception as build_error:
                logger.error("Build failed", exc_info=True)
                error_msg = str(build_error)
                if hasattr(build_error, 'details'):
                    error_msg = f"{error_msg}\nDetails: {build_error.details}"
                click.echo(f"Build failed: {error_msg}", err=True)
                raise click.Abort()
                
        except click.Abort:
            raise
        except Exception as e:
            logger.error("Unexpected error during build", exc_info=True)
            click.echo(f"Build failed: An unexpected error occurred. Check the logs for details.", err=True)
            raise click.Abort()
    
    try:
        asyncio.run(_build())
    except click.Abort:
        exit(1)
    except Exception as e:
        logger.error("Failed to run build", exc_info=True)
        click.echo("Build failed: Could not start the build process. Check the logs for details.", err=True)
        exit(1) 