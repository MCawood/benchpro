"""Service for managing system paths using XDG base directories."""

import os
from pathlib import Path
from typing import Dict

class SystemPaths:
    """Manages system paths following XDG base directory specification."""

    def __init__(self):
        """Initialize system paths."""
        # XDG Base Directory paths
        self.xdg_config_home = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
        self.xdg_cache_home = Path(os.environ.get('XDG_CACHE_HOME', '~/.cache')).expanduser()
        self.xdg_data_home = Path(os.environ.get('XDG_DATA_HOME', '~/.local/share')).expanduser()
        self.xdg_state_home = Path(os.environ.get('XDG_STATE_HOME', '~/.local/state')).expanduser()

        # BenchPro specific paths
        self.config_dir = self.xdg_config_home / 'benchpro'
        self.cache_dir = self.xdg_cache_home / 'benchpro'
        self.data_dir = self.xdg_data_home / 'benchpro'
        self.state_dir = self.xdg_state_home / 'benchpro'

        # Ensure directories exist
        self._ensure_dirs_exist()

    def _ensure_dirs_exist(self) -> None:
        """Create system directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def get_config_file(self, name: str) -> Path:
        """Get path to a configuration file.
        
        Args:
            name: Name of the configuration file
            
        Returns:
            Path to the configuration file
        """
        return self.config_dir / name

    def get_cache_dir(self, subdir: str = None) -> Path:
        """Get path to a cache directory.
        
        Args:
            subdir: Optional subdirectory name
            
        Returns:
            Path to the cache directory
        """
        if subdir:
            path = self.cache_dir / subdir
            path.mkdir(parents=True, exist_ok=True)
            return path
        return self.cache_dir

    def get_data_file(self, name: str) -> Path:
        """Get path to a data file.
        
        Args:
            name: Name of the data file
            
        Returns:
            Path to the data file
        """
        return self.data_dir / name

    def get_state_file(self, name: str) -> Path:
        """Get path to a state file.
        
        Args:
            name: Name of the state file
            
        Returns:
            Path to the state file
        """
        return self.state_dir / name

    def get_log_file(self, name: str) -> Path:
        """Get path to a log file.
        
        Args:
            name: Name of the log file
            
        Returns:
            Path to the log file
        """
        log_dir = self.state_dir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / name 