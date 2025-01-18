"""Central logging configuration for BenchPRO."""

import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logging(debug: bool = False, log_dir: Optional[Path] = None) -> None:
    """Set up logging for BenchPRO.
    
    Args:
        debug: Enable debug logging
        log_dir: Optional directory for log files
    """
    # Create root logger
    root_logger = logging.getLogger("benchpro")
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(console_handler)
    
    # File handler if log directory provided
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "benchpro.log")
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        
        if debug:
            debug_handler = logging.FileHandler(log_dir / "debug.log")
            debug_handler.setFormatter(detailed_formatter)
            debug_handler.setLevel(logging.DEBUG)
            root_logger.addHandler(debug_handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component.
    
    Args:
        name: Component name (e.g., "build", "staging", "executor")
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"benchpro.{name}") 