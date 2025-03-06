"""
Base Extractor for BenchPRO result extraction.

This module defines the BaseExtractor abstract class that all result extractor strategies must implement.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseExtractor(ABC):
    """
    Base class for result extractors.
    
    All result extraction strategies must implement this interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the extractor with configuration data.
        
        Args:
            config: Configuration dictionary for the extractor.
        """
        self.config = config
    
    @abstractmethod
    def extract(self, log_file: str) -> Optional[str]:
        """
        Extract results from the log file.
        
        Args:
            log_file: Path to the log file to extract results from.
            
        Returns:
            Extracted result value as a string or None if extraction failed.
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate the extractor configuration.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        # Base implementation just checks if config exists
        return self.config is not None
    
    def validate_file(self, file_path: str) -> bool:
        """
        Validate that the file exists and is readable.
        
        Args:
            file_path: Path to the file to validate.
            
        Returns:
            True if the file exists and is readable, False otherwise.
        """
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK) 