"""
Result Extractor for BenchPRO.

This module handles extraction of results from benchmark output.
"""

import os
from typing import Dict, Any, Optional, Type

from benchpro.results.extractors import BaseExtractor, RegexExtractor, CommandExtractor
from benchpro.utils.logger import get_logger


class ResultExtractor:
    """
    Main result extractor controller.
    
    This class selects and uses the appropriate extractor strategy based on configuration.
    """
    
    # Registry of extractor types
    _extractors = {
        "regex": RegexExtractor,
        "command": CommandExtractor,
    }
    
    def __init__(self):
        """Initialize the ResultExtractor."""
        self.logger = get_logger(__name__)
    
    def extract_results(self, log_file: str, extraction_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract results from a benchmark log file.
        
        Args:
            log_file: Path to the log file.
            extraction_config: Result extraction configuration.
                Must contain 'method' key with one of the registered extractor types.
                
        Returns:
            Dictionary with extraction results.
        """
        self.logger.info(f"Extracting results from {log_file}")
        
        if not os.path.isfile(log_file):
            self.logger.error(f"Log file not found: {log_file}")
            return {"success": False, "error": "Log file not found"}
        
        # Check if extraction config is valid
        if not extraction_config:
            self.logger.error("No extraction configuration provided")
            return {"success": False, "error": "No extraction configuration provided"}
        
        method = extraction_config.get("method")
        if not method:
            self.logger.error("No extraction method specified")
            return {"success": False, "error": "No extraction method specified"}
        
        # Check if the method is supported
        if method not in self._extractors:
            self.logger.error(f"Unsupported extraction method: {method}")
            return {"success": False, "error": f"Unsupported extraction method: {method}"}
        
        # Get the extractor class
        extractor_class = self._extractors[method]
        
        # Create the extractor
        try:
            extractor = extractor_class(extraction_config)
        except Exception as e:
            self.logger.error(f"Error creating extractor: {str(e)}")
            return {"success": False, "error": f"Error creating extractor: {str(e)}"}
        
        # Extract results
        try:
            result = extractor.extract(log_file)
            
            if result is None:
                self.logger.warning("Extraction returned no result")
                return {"success": False, "error": "Extraction returned no result"}
            
            # Create result dictionary
            # Handle both string and dictionary formats for metric
            if isinstance(extraction_config.get("metric"), dict):
                # Legacy format where metric is a dictionary with name and unit
                metric_name = extraction_config.get("metric", {}).get("name", "value")
                metric_unit = extraction_config.get("metric", {}).get("unit", "")
            else:
                # New format where metric is a string and unit is separate
                metric_name = extraction_config.get("metric", "value")
                metric_unit = extraction_config.get("unit", "")
            
            return {
                "success": True,
                "metric": {
                    "name": metric_name,
                    "value": result,
                    "unit": metric_unit
                },
                "raw_value": result
            }
            
        except Exception as e:
            self.logger.error(f"Error during extraction: {str(e)}")
            return {"success": False, "error": f"Error during extraction: {str(e)}"}
    
    @classmethod
    def register_extractor(cls, name: str, extractor_class: Type[BaseExtractor]) -> None:
        """
        Register a new extractor type.
        
        Args:
            name: Name of the extractor.
            extractor_class: Extractor class to register.
        """
        if not issubclass(extractor_class, BaseExtractor):
            raise TypeError(f"Extractor class must be a subclass of BaseExtractor")
        
        cls._extractors[name] = extractor_class 