"""Build logging functionality."""

import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BuildLogEntry:
    """A single build log entry."""
    timestamp: datetime
    stream: str  # 'stdout' or 'stderr'
    content: str

class BuildLogger:
    """Handles logging for the build process."""

    def __init__(self, log_dir: Path):
        """Initialize build logger.
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = log_dir
        self.stdout_file = log_dir / "build.out"
        self.stderr_file = log_dir / "build.err"
        self.summary_file = log_dir / "build.log"
        
        # Set up internal logger
        self.logger = logging.getLogger("benchpro.build")
        self.formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Create file handlers
        self.stdout_handler = logging.FileHandler(self.stdout_file)
        self.stderr_handler = logging.FileHandler(self.stderr_file)
        self.summary_handler = logging.FileHandler(self.summary_file)
        
        # Set formatters
        self.stdout_handler.setFormatter(self.formatter)
        self.stderr_handler.setFormatter(self.formatter)
        self.summary_handler.setFormatter(self.formatter)
        
        # Add handlers
        self.logger.addHandler(self.stdout_handler)
        self.logger.addHandler(self.stderr_handler)
        self.logger.addHandler(self.summary_handler)
        
        # Initialize log entries
        self.entries: List[BuildLogEntry] = []
        
        # Error patterns to detect in stderr
        self.error_patterns = [
            re.compile(r'error:', re.IGNORECASE),
            re.compile(r'undefined reference'),
            re.compile(r'cannot find'),
            re.compile(r'no such file'),
            re.compile(r'failed'),
            re.compile(r'fatal:'),
        ]
    
    def log_stdout(self, content: str) -> None:
        """Log stdout content.
        
        Args:
            content: Content to log
        """
        timestamp = datetime.now()
        self.entries.append(BuildLogEntry(timestamp, 'stdout', content))
        with open(self.stdout_file, 'a') as f:
            f.write(f"[{timestamp.isoformat()}] {content}\n")
    
    def log_stderr(self, content: str) -> None:
        """Log stderr content.
        
        Args:
            content: Content to log
        """
        timestamp = datetime.now()
        self.entries.append(BuildLogEntry(timestamp, 'stderr', content))
        with open(self.stderr_file, 'a') as f:
            f.write(f"[{timestamp.isoformat()}] {content}\n")
    
    def log_summary(self, message: str, level: str = 'INFO') -> None:
        """Log a summary message.
        
        Args:
            message: Message to log
            level: Log level (default: INFO)
        """
        with open(self.summary_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] {level} - {message}\n")
    
    def has_errors(self) -> bool:
        """Check if there are any errors in the build logs.
        
        Returns:
            True if errors were detected, False otherwise
        """
        # Read stderr content
        if not self.stderr_file.exists():
            return False
            
        stderr_content = self.stderr_file.read_text()
        
        # Check for error patterns
        for pattern in self.error_patterns:
            if pattern.search(stderr_content):
                return True
        
        return False
    
    def get_error_context(self) -> Optional[str]:
        """Get context around errors in the build logs.
        
        Returns:
            String containing error context if errors found, None otherwise
        """
        if not self.has_errors():
            return None
            
        # Read stderr content
        stderr_content = self.stderr_file.read_text()
        
        # Find error lines and surrounding context
        error_contexts = []
        lines = stderr_content.split('\n')
        for i, line in enumerate(lines):
            for pattern in self.error_patterns:
                if pattern.search(line):
                    # Get up to 3 lines before and after the error
                    start = max(0, i - 3)
                    end = min(len(lines), i + 4)
                    context = '\n'.join(lines[start:end])
                    error_contexts.append(context)
        
        return '\n\n'.join(error_contexts) if error_contexts else None
    
    def get_build_summary(self) -> Dict[str, Any]:
        """Get a summary of the build process.
        
        Returns:
            Dictionary containing build summary information
        """
        return {
            'stdout_size': self.stdout_file.stat().st_size if self.stdout_file.exists() else 0,
            'stderr_size': self.stderr_file.stat().st_size if self.stderr_file.exists() else 0,
            'has_errors': self.has_errors(),
            'error_context': self.get_error_context(),
            'entry_count': len(self.entries),
            'first_entry': self.entries[0].timestamp if self.entries else None,
            'last_entry': self.entries[-1].timestamp if self.entries else None,
        }
    
    def cleanup(self) -> None:
        """Clean up logging handlers."""
        self.logger.removeHandler(self.stdout_handler)
        self.logger.removeHandler(self.stderr_handler)
        self.logger.removeHandler(self.summary_handler)
        self.stdout_handler.close()
        self.stderr_handler.close()
        self.summary_handler.close() 