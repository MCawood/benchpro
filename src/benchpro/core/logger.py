import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Create a global console instance for logging (stderr)
console = Console(stderr=True)

def setup_logging(level: str = "INFO", log_file: Optional[Path] = None):
    """
    Configure logging for BenchPro.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to a log file
    """
    # Create the root logger
    root_logger = logging.getLogger("benchpro")
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []
    
    # Create console handler with Rich
    # We use stderr for logging to keep stdout clean for command output if needed
    console_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True
    )
    console_handler.setLevel(level)
    
    # Format for console (Rich handles most of it, but we can customize if needed)
    # console_formatter = logging.Formatter("%(message)s")
    # console_handler.setFormatter(console_formatter)
    
    root_logger.addHandler(console_handler)
    
    # Create file handler if requested
    if log_file:
        # Ensure directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG) # Always log debug to file
        
        # Detailed format for file
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(file_handler)
        
    # Set third-party loggers to WARNING to avoid noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

def get_logger(name: str = "benchpro"):
    """Get a logger instance."""
    return logging.getLogger(name)
