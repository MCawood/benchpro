import os
import shutil
import re
import socket
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    name: str = "default"
    host_patterns: List[str] = Field(default_factory=list)
    platform_patterns: List[str] = Field(default_factory=list)
    scheduler: str = "local"
    default_walltime: int = 3600
    max_walltime: int = 86400
    max_local_tasks: int = 8
    account: Optional[str] = None
    partition: Optional[str] = None


class Config(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    systems: Dict[str, SystemConfig] = Field(default_factory=dict)
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
            
            # Site config
            site_config = os.environ.get("BENCHPRO_SITE_CONFIG")
            if site_config:
                config_paths.append(Path(site_config))
            else:
                config_paths.append(Path("/etc/benchpro/config.yaml"))

            # User config
            config_dir = os.environ.get("BENCHPRO_CONFIG_DIR")
            if config_dir:
                user_config_dir = Path(config_dir)
            else:
                user_config_dir = Path.home() / ".config/benchpro"
            
            user_config_path = user_config_dir / "config.yaml"
            
            # Auto-init if missing
            if not user_config_path.exists():
                cls._init_user_config(user_config_dir)

            config_paths.append(user_config_path)
            config_paths.append(Path.cwd() / ".benchpro/config.yaml")
            
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
        from benchpro.core.templating import TemplateEngine
        
        # Add env vars to context
        env_context = {k: v for k, v in os.environ.items()}
        
        # Initial context with config data and env
        # We need to resolve systems first to detect the active one
        context = {
            "env": env_context,
            **config_data,
        }
        
        engine = TemplateEngine(context)
        resolved_data = engine.render(config_data)
        
        # Create instance to parse systems
        config = cls(**resolved_data)
        
        # Detect System
        active_system = None
        
        # 1. Check env var override
        env_system = os.environ.get("BENCHPRO_SYSTEM")
        if env_system and env_system in config.systems:
            active_system = config.systems[env_system]
        
        # 2. Check platform/OS matching
        if not active_system:
            current_platform = platform.system().lower()  # e.g., "darwin", "linux", "windows"
            for sys_name, sys_cfg in config.systems.items():
                for pattern in sys_cfg.platform_patterns:
                    if re.match(pattern, current_platform, re.IGNORECASE):
                        active_system = sys_cfg
                        break
                if active_system:
                    break
        
        # 3. Check hostname matching
        if not active_system:
            hostname = socket.getfqdn()
            for sys_name, sys_cfg in config.systems.items():
                for pattern in sys_cfg.host_patterns:
                    if re.match(pattern, hostname):
                        active_system = sys_cfg
                        break
                if active_system:
                    break
        
        # 4. Fallback to existing 'system' field or default
        if active_system:
            # Merge active system into the main 'system' field
            # This allows code to just access config.system
            # We merge the active system ON TOP of the existing default system
            merged_system = config.system.model_dump()
            merged_system.update(active_system.model_dump(exclude_unset=True))
            config.system = SystemConfig(**merged_system)
            
        return config

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

    @staticmethod
    def _init_user_config(config_dir: Path):
        """
        Initialize user configuration directory.
        """
        print(f"First run detected. Initializing configuration in {config_dir}")
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "profiles").mkdir(exist_ok=True)
        
        # Create default config
        config_path = config_dir / "config.yaml"
        
        # Check for site config to copy from
        site_config = os.environ.get("BENCHPRO_SITE_CONFIG")
        if site_config and os.path.exists(site_config):
             # We could copy site config as a base, but usually we want a minimal user config
             # For now, let's write a minimal default
             pass
        
        # Write minimal default with darwin system profile
        with open(config_path, "w") as f:
            yaml.dump({
                "system": {
                    "name": "default",
                    "scheduler": "local"
                },
                "systems": {
                    "darwin": {
                        "name": "darwin",
                        "platform_patterns": ["darwin"],
                        "scheduler": "local",
                        "default_walltime": 3600,
                        "max_walltime": 86400,
                        "max_local_tasks": 4
                    }
                },
                "defaults": {
                    "root_dir": str(Path.home() / "benchpro")
                }
            }, f)
