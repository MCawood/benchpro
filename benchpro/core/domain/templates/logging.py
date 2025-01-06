"""Logging configuration for the template system."""
import logging
from typing import Optional
from pathlib import Path

# Create logger
logger = logging.getLogger("benchpro.templates")

def setup_logging(log_level: int = logging.INFO, log_file: Optional[Path] = None) -> None:
    """Set up logging for the template system.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional path to log file
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Set log level
    logger.setLevel(log_level)

def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component.
    
    Args:
        name: Component name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"benchpro.templates.{name}") 