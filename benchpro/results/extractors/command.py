"""
Command-line based result extractor for BenchPRO.

This module implements a command-line tool based strategy for extracting results from benchmark output.
"""

import os
import subprocess
from typing import Dict, Any, Optional, Union
import re

from benchpro.results.extractors.base import BaseExtractor
from benchpro.utils.logger import get_logger


class CommandExtractor(BaseExtractor):
    """
    Result extractor that uses command-line tools (grep, awk, sed, etc.) to extract data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the command extractor.
        
        Args:
            config: Configuration dictionary with the following keys:
                command: Command to execute for extraction (e.g., "grep 'Hello, World!'").
                shell: Whether to use shell=True in subprocess (defaults to True).
        """
        super().__init__(config)
        self.logger = get_logger(__name__)
        self.command = self.config.get("command", "")
        self.use_shell = self.config.get("shell", True)
    
    def validate_config(self) -> bool:
        """
        Validate the command extractor configuration.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        if not super().validate_config():
            return False
        
        if not self.command:
            self.logger.error("No command specified in command extractor configuration")
            return False
        
        return True
    
    def extract(self, log_file: str) -> Optional[str]:
        """
        Extract results from the log file using command-line tools.
        
        Args:
            log_file: Path to the log file to extract results from.
            
        Returns:
            Extracted result value or None if extraction failed.
        """
        if not self.validate_file(log_file):
            self.logger.error(f"Log file not found or not readable: {log_file}")
            return None
        
        if not self.validate_config():
            self.logger.error("Invalid command extractor configuration")
            return None
        
        try:
            # Get the command from the configuration
            command = self.command
            
            # Replace {log_file} with the actual log file path
            if "{log_file}" in command:
                command = command.replace("{log_file}", log_file)
            else:
                # Use cat to pipe the log file to the command if {log_file} is not in the command
                command = f"cat '{log_file}' | {command}"
            
            self.logger.debug(f"Running command: {command}")
            
            # Run the command
            process = subprocess.run(
                command,
                shell=True,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            if process.returncode != 0:
                self.logger.error(f"Command execution failed: {process.stderr}")
                return None
            
            # Get the output and strip whitespace
            result = process.stdout.strip()
            
            # If empty result, return None
            if not result:
                self.logger.warning("Command returned empty result")
                return None
            
            # Try to extract a numeric value if the result contains non-numeric characters
            # First check if the result is already a clean numeric value
            if re.match(r'^\d+\.?\d*$', result):
                self.logger.info(f"Result is already a clean numeric value: {result}")
                return result
            
            # Otherwise, try to extract a numeric value with a more permissive pattern
            # This can handle formats like "Result: 123.45 seconds" or "Time: 123.45"
            numeric_match = re.search(r'(?:^|[^\d])(\d+\.?\d*)\s*(?:$|[^\d])', result)
            if numeric_match:
                numeric_result = numeric_match.group(1)
                self.logger.info(f"Extracted numeric result: {numeric_result} from {result}")
                return numeric_result
            
            # If there are multiple numbers, find the most likely one
            # Often this would be the largest number or one that appears in a specific context
            all_numbers = re.findall(r'(\d+\.?\d*)', result)
            if all_numbers:
                # Default to the first number found
                numeric_result = all_numbers[0]
                self.logger.info(f"Found multiple numeric values, using first one: {numeric_result} from {result}")
                return numeric_result
            
            self.logger.info(f"No numeric value found, returning full result: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting result with command: {str(e)}")
            return None 