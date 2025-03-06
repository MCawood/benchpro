"""
Logging Module for BenchPRO.

This module provides centralized logging functionality with timestamped log files.
"""

import os
import logging
import datetime
from typing import Optional

from benchpro.utils.user_dir import user_dir_manager

class BenchProLogger:
    """
    Centralized logger for BenchPRO.
    
    Responsibilities:
    - Configure logging with appropriate handlers
    - Create timestamped log files
    - Provide access to loggers for different modules
    """
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of BenchProLogger."""
        # Check if we're in completion mode
        if "_BP_COMPLETE" in os.environ:
            # In completion mode, don't create a real instance
            if cls._instance is None:
                cls._instance = cls._create_null_instance()
        else:
            # Normal mode, create a real instance
            if cls._instance is None:
                cls._instance = BenchProLogger()
        return cls._instance
    
    @classmethod
    def _create_null_instance(cls):
        """Create a null instance that doesn't initialize logging."""
        instance = BenchProLogger.__new__(BenchProLogger)
        instance.initialized = True
        instance.log_level = logging.CRITICAL
        instance.log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        instance.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        instance.log_file = "/dev/null"
        return instance
    
    def __init__(self):
        """Initialize the BenchProLogger."""
        # Only initialize once
        if BenchProLogger._instance is not None:
            return
            
        self.initialized = False
        
        # Default log level
        self.log_level = logging.INFO
        
        # We'll check for user settings when setup_logging is called to avoid circular imports
        self.log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = None
        
        # Initialize logging
        self.setup_logging()
        
        # Store the instance
        BenchProLogger._instance = self
    
    def _get_log_level(self, level_str: str) -> int:
        """Convert a string log level to its numeric value."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "WARN": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        return level_map.get(level_str.upper(), logging.INFO)
    
    def setup_logging(self, log_level: Optional[int] = None):
        """
        Set up logging with appropriate handlers.
        
        Args:
            log_level: Optional log level to use. If None, uses the default level.
        """
        if self.initialized:
            return
            
        # Set log level if provided
        if log_level is not None:
            self.log_level = log_level
        else:
            # Check if we should use the user's configured log level
            try:
                settings = user_dir_manager.load_settings()
                logging_level_str = settings.get("logging_level", "INFO")
                self.log_level = self._get_log_level(logging_level_str)
            except Exception:
                # Keep the existing log level
                pass
            
        # Create timestamped log file
        self.log_file = user_dir_manager.get_path("logs", f"benchpro_{self.timestamp}.log")
        user_dir_manager.ensure_file_directory(self.log_file)
        
        # Configure root logger
        logging.basicConfig(
            level=self.log_level,
            format=self.log_format,
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        
        # Create a link to the latest log file
        latest_log = user_dir_manager.get_path("logs", "benchpro_latest.log")
        try:
            if os.path.exists(latest_log):
                os.remove(latest_log)
            # Create a symbolic link on Unix-like systems
            if os.name != 'nt':  # Not Windows
                os.symlink(self.log_file, latest_log)
            else:
                # On Windows, just copy the file
                import shutil
                shutil.copy2(self.log_file, latest_log)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to create link to latest log: {e}")
            
        self.initialized = True
        
        # Log initialization
        logging.getLogger(__name__).info(f"Logging initialized. Log file: {self.log_file}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.
        
        Args:
            name: Name of the logger.
            
        Returns:
            Logger instance.
        """
        return logging.getLogger(name)
    
    def get_log_file(self) -> str:
        """
        Get the path to the current log file.
        
        Returns:
            Path to the log file.
        """
        return self.log_file

# Create a singleton instance
logger_instance = BenchProLogger.get_instance()

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified name.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance
    """
    # Check if we're in completion mode
    if "_BP_COMPLETE" in os.environ:
        # In completion mode, return a null logger
        logger = logging.getLogger(name)
        logger.addHandler(logging.NullHandler())
        return logger
    
    # Normal mode, use the BenchProLogger
    return BenchProLogger.get_instance().get_logger(name)

def get_log_file() -> str:
    """
    Get the path to the current log file.
    
    Returns:
        Path to the current log file
    """
    # Check if we're in completion mode
    if "_BP_COMPLETE" in os.environ:
        # In completion mode, return a dummy path
        return "/dev/null"
    
    # Normal mode, use the BenchProLogger
    return BenchProLogger.get_instance().get_log_file()

def setup_logging(log_level: Optional[int] = None):
    """
    Set up logging with the specified log level.
    
    Args:
        log_level: Log level to use. If None, uses the default log level.
    """
    # Check if we're in completion mode
    if "_BP_COMPLETE" in os.environ:
        # In completion mode, disable logging
        logging.disable(logging.CRITICAL)
        return
    
    # Normal mode, use the BenchProLogger
    BenchProLogger.get_instance().setup_logging(log_level) 