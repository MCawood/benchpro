"""Template service for managing application templates."""
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from benchpro.core.domain.templates import (
    TemplateLoader,
    TemplateConfig,
    TemplateRenderer,
    TemplateNotFoundError,
    TemplateConfigError,
    TemplateRenderError,
    TemplateValidationError,
    TemplateVariableError,
    TemplateSyntaxError
)

logger = logging.getLogger("benchpro.templates.service")

class TemplateService:
    """Service for managing application templates."""

    def __init__(self, template_dir: Path):
        """Initialize template service.

        Args:
            template_dir: Root directory containing templates.
        """
        self.template_dir = Path(template_dir)
        self.loader = TemplateLoader(self.template_dir)
        logger.info(f"Initialized template service with directory: {template_dir}")

    def list_applications(self) -> List[str]:
        """List available application templates.

        Returns:
            List of application names.
        """
        logger.debug("Listing available applications")
        return self.loader.list_applications()

    def load_template(self, name: str, template_file: str, version: Optional[str] = None) -> Tuple[TemplateConfig, str]:
        """Load a template and its configuration.

        Args:
            name: Template name.
            template_file: Name of the template file to load.
            version: Optional version string. If not provided, loads the default version.

        Returns:
            Tuple of (template configuration, template content).

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            TemplateConfigError: If configuration is invalid.
            TemplateValidationError: If template is invalid.
        """
        try:
            logger.debug(f"Loading template '{name}' version {version or 'latest'}")
            config = self.loader.load_config(name, version)
            template = self.loader.load_template(name, template_file, version)
            logger.info(f"Successfully loaded template '{name}' version {config.version}")
            return config, template
        except (TemplateNotFoundError, TemplateConfigError, TemplateValidationError):
            raise

    def render_template(self, name: str, template_file: str, context: Dict[str, Any], version: Optional[str] = None) -> str:
        """Render a template with the given context.

        Args:
            name: Template name.
            template_file: Name of the template file to render.
            context: Template context containing variables.
            version: Optional version string. If not provided, uses the default version.

        Returns:
            Rendered template content.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            TemplateConfigError: If configuration is invalid.
            TemplateRenderError: If template cannot be rendered.
            TemplateVariableError: If required variables are missing.
            TemplateSyntaxError: If template syntax is invalid.
        """
        try:
            logger.debug(f"Loading template '{name}' version {version or 'latest'}")
            # Load template and config
            config = self.loader.load_config(name, version)
            template_content = self.loader.load_template(name, template_file, version)

            logger.debug("Creating template renderer")
            # Create renderer and render template
            renderer = TemplateRenderer(config, template_content)
            result = renderer.render(context)

            logger.info(f"Successfully rendered template '{name}' version {config.version}")
            return result
        except (
            TemplateNotFoundError,
            TemplateConfigError,
            TemplateRenderError,
            TemplateVariableError,
            TemplateSyntaxError
        ):
            raise
        except Exception as e:
            logger.error(f"Failed to render template '{name}': {e}")
            raise TemplateRenderError(f"Failed to render template '{name}': {e}")

    def validate_template(self, name: str, version: Optional[str] = None) -> None:
        """Validate a template.

        Args:
            name: Template name.
            version: Optional version string. If not provided, validates the default version.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            TemplateConfigError: If configuration is invalid.
            TemplateValidationError: If template is invalid.
        """
        try:
            logger.debug(f"Validating template '{name}' version {version or 'latest'}")
            self.loader.load_config(name, version)
            logger.info(f"Successfully validated template '{name}'")
        except (TemplateNotFoundError, TemplateConfigError, TemplateValidationError):
            raise 