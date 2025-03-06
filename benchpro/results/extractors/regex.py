"""
Regex-based result extractor for BenchPRO.

This module implements a regex-based strategy for extracting results from benchmark output.
"""

import re
import logging
from typing import Dict, Any, Optional, Union

from benchpro.results.extractors.base import BaseExtractor
from benchpro.utils.logger import get_logger


class RegexExtractor(BaseExtractor):
    """
    Result extractor that uses regular expressions to extract data from benchmark output.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the regex extractor.
        
        Args:
            config: Configuration dictionary with the following keys:
                pattern: Regular expression pattern with capture groups.
                group: Optional index of the capture group to extract (defaults to 0).
        """
        super().__init__(config)
        self.logger = get_logger(__name__)
        
        # Compile the pattern
        self.pattern = None
        if "pattern" in self.config:
            try:
                self.pattern = re.compile(self.config["pattern"])
            except re.error as e:
                self.logger.error(f"Invalid regex pattern: {str(e)}")
        
        # Use group 0 (whole match) by default
        self.group = self.config.get("group", 0)
    
    def validate_config(self) -> bool:
        """
        Validate the regex extractor configuration.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        if not super().validate_config():
            return False
        
        if "pattern" not in self.config:
            self.logger.error("No pattern specified in regex extractor configuration")
            return False
        
        return self.pattern is not None
    
    def extract(self, log_file: str) -> Optional[str]:
        """
        Extract results from the log file using regex.
        
        Args:
            log_file: Path to the log file to extract results from.
            
        Returns:
            Extracted result value or None if extraction failed.
        """
        if not self.validate_file(log_file):
            self.logger.error(f"Log file not found or not readable: {log_file}")
            return None
        
        if not self.validate_config():
            self.logger.error("Invalid regex extractor configuration")
            return None
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
            # Search for the pattern
            match = self.pattern.search(content)
            if not match:
                self.logger.warning(f"Pattern not found in log file: {self.config['pattern']}")
                return None
            
            # Extract the captured group (group 1 is typically the first capture group)
            try:
                if match.groups() and len(match.groups()) > 0:
                    # Use the first capture group if available
                    result = match.group(1)
                    self.logger.info(f"Extracted value: {result} (from group 1)")
                else:
                    # Fall back to the entire match
                    result = match.group(0)
                    self.logger.info(f"Extracted value: {result} (from entire match)")
            except IndexError:
                self.logger.error(f"Capture group not found in match")
                return None
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting result with regex: {str(e)}")
            return None 