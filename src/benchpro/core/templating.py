import os
import re
from typing import Any, Dict, Optional
from jinja2 import Environment, StrictUndefined, BaseLoader, TemplateSyntaxError

class TemplateEngine:
    def __init__(self, context: Dict[str, Any] = None):
        self.context = context or {}
        self.env = Environment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
            autoescape=False
        )
        
    def render(self, content: Any, context_override: Dict[str, Any] = None) -> Any:
        """
        Recursively render strings in a data structure (dict, list, str).
        Supports ${var} syntax by converting to {{var}} before rendering.
        """
        ctx = self.context.copy()
        if context_override:
            ctx.update(context_override)
            
        if isinstance(content, str):
            return self._render_string(content, ctx)
        elif isinstance(content, dict):
            return {k: self.render(v, ctx) for k, v in content.items()}
        elif isinstance(content, list):
            return [self.render(item, ctx) for item in content]
        else:
            return content

    def _render_string(self, text: str, context: Dict[str, Any]) -> str:
        # Convert ${var} to {{var}}
        # We look for ${...} patterns and replace them
        # This is a basic implementation; complex nested braces might need more care
        # but for ${var} and ${var.attr} it works well.
        
        # Regex to find ${...} but not \${...} (escaped)
        # We'll just do a simple replace for now as per requirements
        jinja_text = re.sub(r'\$\{([^}]+)\}', r'{{\1}}', text)
        
        try:
            template = self.env.from_string(jinja_text)
            return template.render(**context)
        except Exception as e:
            # In a real scenario we might want to fail hard or pass through
            # For now, we fail hard as per R-TPL-001 (strict undefined)
            raise ValueError(f"Failed to render template '{text}': {e}")
