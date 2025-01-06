"""Template loading functionality."""
import logging
from pathlib import Path
from typing import List, Optional
import yaml

from .config import TemplateConfig
from .exceptions import (
    TemplateNotFoundError,
    TemplateConfigError,
    TemplateValidationError
)

logger = logging.getLogger("benchpro.templates.loader")

class TemplateLoader:
    """Loads template files and configurations."""

    def __init__(self, root_dir: Path):
        """Initialize template loader.

        Args:
            root_dir: Root directory containing templates.
        """
        self.root_dir = root_dir
        self.applications_dir = root_dir / "applications"
        if not self.applications_dir.exists():
            logger.warning(f"Applications directory not found: {self.applications_dir}")
            self.applications_dir.mkdir(parents=True)

    def list_applications(self) -> List[str]:
        """List available application templates.

        Returns:
            List of application names.
        """
        if not self.applications_dir.exists():
            logger.warning("Applications directory does not exist")
            return []

        return [d.name for d in self.applications_dir.iterdir() if d.is_dir()]

    def load_config(self, name: str, version: Optional[str] = None) -> TemplateConfig:
        """Load template configuration.

        Args:
            name: Template name.
            version: Optional version string. If not provided, loads the default version.

        Returns:
            Template configuration.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            TemplateConfigError: If configuration is invalid.
            TemplateValidationError: If configuration is missing required fields.
        """
        template_path = self.applications_dir / name
        if not template_path.exists():
            logger.error(f"Application template not found: {template_path}")
            raise TemplateNotFoundError(f"Application template '{name}' not found")

        if version:
            # Try both with and without 'v' prefix
            version_path = template_path / f"v{version}"
            if not version_path.exists():
                version_path = template_path / version
            if not version_path.exists():
                logger.error(f"Version '{version}' not found for template '{name}'")
                raise TemplateNotFoundError(f"Version '{version}' not found for template '{name}'")
            template_path = version_path

        config_path = template_path / "config.yaml"
        if not config_path.exists():
            logger.error(f"Template config not found: {config_path}")
            raise TemplateNotFoundError(f"Configuration file not found for template '{name}'")

        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                if not config_data:
                    raise TemplateConfigError("Empty configuration file")
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file: {e}")
            raise TemplateConfigError(f"Invalid YAML in configuration file: {e}")

        try:
            return TemplateConfig(config_data)
        except TemplateValidationError as e:
            logger.error(f"Invalid template configuration: {e}")
            raise

    def load_template(self, name: str, template_file: str, version: Optional[str] = None) -> str:
        """Load template file.

        Args:
            name: Template name.
            template_file: Name of the template file to load.
            version: Optional version string. If not provided, loads the default version.

        Returns:
            Template content.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            TemplateValidationError: If template file is empty.
        """
        template_path = self.applications_dir / name
        if not template_path.exists():
            logger.error(f"Application template not found: {template_path}")
            raise TemplateNotFoundError(f"Application template '{name}' not found")

        if version:
            # Try both with and without 'v' prefix
            version_path = template_path / f"v{version}"
            if not version_path.exists():
                version_path = template_path / version
            if not version_path.exists():
                logger.error(f"Version '{version}' not found for template '{name}'")
                raise TemplateNotFoundError(f"Version '{version}' not found for template '{name}'")
            template_path = version_path

        template_file_path = template_path / template_file
        if not template_file_path.exists():
            logger.error(f"Template file not found: {template_file_path}")
            raise TemplateNotFoundError(f"Template file '{template_file}' not found")

        content = template_file_path.read_text()
        if not content:
            logger.error(f"Empty template file: {template_file_path}")
            raise TemplateValidationError("Empty template file")

        return content 