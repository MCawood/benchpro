"""Template rendering functionality."""

import logging
from typing import Dict, Any
from jinja2 import Environment, StrictUndefined, TemplateError as Jinja2TemplateError
from jinja2.exceptions import TemplateSyntaxError as Jinja2TemplateSyntaxError
from .exceptions import TemplateVariableError, TemplateSyntaxError, TemplateRenderError

logger = logging.getLogger(__name__)

class TemplateRenderer:
    """Template renderer using Jinja2."""

    def __init__(self, config: Any, template: str):
        """Initialize template renderer.

        Args:
            config: Template configuration.
            template: Template string.
        """
        self.config = config
        self.template = template
        self.env = Environment(undefined=StrictUndefined)

    def render(self, context: Dict[str, Any]) -> str:
        """Render template with context.

        Args:
            context: Template context containing variables.

        Returns:
            Rendered template.

        Raises:
            TemplateVariableError: If required variables are missing.
            TemplateSyntaxError: If template syntax is invalid.
            TemplateRenderError: If template cannot be rendered.
        """
        logger.debug("Validating template context")
        self._validate_context(context)

        logger.debug("Creating template context with config and overrides")
        template_context = self._create_context(context)

        try:
            # Check for include statements
            if "{% include" in self.template:
                logger.error("Template includes are not supported")
                raise TemplateSyntaxError("Template includes are not supported")

            logger.debug("Parsing template")
            jinja_template = self.env.from_string(self.template)

            logger.debug("Rendering template with context")
            result = jinja_template.render(**template_context)

            # Normalize line endings and remove trailing whitespace
            lines = [line.rstrip() for line in result.splitlines()]
            rendered = '\n'.join(lines)

            logger.info("Successfully rendered template")
            return rendered

        except Jinja2TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            raise TemplateSyntaxError(f"Invalid template syntax: {e}")
        except Jinja2TemplateError as e:
            error_msg = str(e)
            if "undefined" in error_msg.lower():
                if "is undefined" in error_msg:
                    # Extract the undefined variable name
                    var_name = error_msg.split("'")[1]
                    error = f"Undefined template variable: {var_name}"
                    logger.error(error)
                    raise TemplateVariableError(error)
                elif "has no attribute" in error_msg:
                    # Extract the undefined attribute path from template
                    var_parts = self.template.split("{{")[1].split("}}")[0].strip().split(".")
                    error = f"Undefined template variable: {'.'.join(var_parts[:2])}"
                    logger.error(error)
                    raise TemplateVariableError(error)
            else:
                logger.error(f"Template render error: {e}")
                raise TemplateRenderError(f"Failed to render template: {e}")

    def _validate_context(self, context: Dict[str, Any]) -> None:
        """Validate template context.

        Args:
            context: Template context to validate.

        Raises:
            TemplateVariableError: If required variables are missing.
        """
        required_vars = {'working_dir', 'install_dir'}
        missing = required_vars - set(context.keys())
        if missing:
            error = f"Missing required context variable: {missing.pop()}"
            logger.error(error)
            raise TemplateVariableError(error)

    def _create_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create template context by merging config with overrides.

        Args:
            context: Context overrides.

        Returns:
            Merged template context.
        """
        # Start with config values as a dictionary
        template_context = {
            'name': self.config.name,
            'version': str(self.config.version),
            'type': self.config.type,
            'build': self.config.build.dict() if hasattr(self.config.build, 'dict') else self.config.build,
            'source': self.config.source,
            'variables': self.config.variables
        }

        # Add optional description if present
        if self.config.description:
            template_context['description'] = self.config.description

        # Deep merge context overrides
        for key, value in context.items():
            if key in template_context and isinstance(template_context[key], dict):
                if isinstance(value, dict):
                    template_context[key] = self._deep_merge(template_context[key].copy(), value)
                else:
                    template_context[key] = value
            else:
                template_context[key] = value

        return template_context

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge source dict into target dict.

        Args:
            target: Target dictionary to merge into.
            source: Source dictionary to merge from.

        Returns:
            Merged dictionary.
        """
        result = target.copy()
        for key, value in source.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result 