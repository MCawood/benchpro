import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    name: str = "default"
    default_walltime: int = 3600
    max_walltime: int = 86400
    max_local_tasks: int = 8


class Config(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    defaults: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def load(cls, config_paths: List[Path] = None) -> "Config":
        """
        Load configuration from multiple layers.
        Precedence: Defaults < Site < System < User < Local
        """
        # Start with defaults
        config_data = {}
        
        # Define search paths if not provided
        if config_paths is None:
            config_paths = []
            
            # Check env var first
            env_path = os.environ.get("BENCHPRO_CONFIG")
            if env_path:
                config_paths.append(Path(env_path))
            
            # Standard paths
            config_paths.extend([
                Path("/etc/benchpro/config.yaml"),
                Path.home() / ".config/benchpro/config.yaml",
                Path.cwd() / ".benchpro/config.yaml",
            ])
            
        # Load and merge
        # Merge all layers
        for path in config_paths:
            if path.exists():
                try:
                    with open(path, "r") as f:
                        layer = yaml.safe_load(f)
                        if layer:
                            config_data = cls._deep_merge(config_data, layer)
                except Exception as e:
                    print(f"Warning: Failed to load config from {path}: {e}")
        
        # Interpolate variables
        # We construct a context from the merged config itself
        # This allows ${system.name} to be used elsewhere
        from benchpro.core.templating import TemplateEngine
        
        # Add env vars to context
        env_context = {k: v for k, v in os.environ.items()}
        
        # Ensure system defaults are present in context
        # We instantiate SystemConfig with the raw data to get defaults
        raw_system = config_data.get("system", {})
        system_defaults = cls.model_fields["system"].default_factory().model_dump()
        # Update defaults with raw data
        # Note: We can't use SystemConfig(**raw_system) directly if raw_system contains variables
        # that would cause validation errors (e.g. int field having "${var}").
        # But SystemConfig fields are mostly simple types. 
        # For now, let's just use the default factory and merge raw on top for the context.
        # Actually, if we want ${system.max_walltime} to resolve to the default 86400 if not set,
        # we need that value in the context.
        
        system_context = system_defaults.copy()
        system_context.update(raw_system)
        
        # Initial context with config data and env
        context = {
            "env": env_context,
            **config_data,
            "system": system_context # Override system with defaults included
        }
        
        # Render the config against itself
        # We might need multiple passes if variables reference other variables
        # For now, single pass
        engine = TemplateEngine(context)
        resolved_data = engine.render(config_data)
                    
        return cls(**resolved_data)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        """
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
