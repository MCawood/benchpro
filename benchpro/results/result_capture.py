"""
Result Capture Module for BenchPRO.

This module handles capturing job output and provenance data.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional, List

from benchpro.results.result_extractor import ResultExtractor
from benchpro.config.config_manager import ConfigManager
from benchpro.utils.logger import get_logger


class ResultCapture:
    """
    Captures and stores job results and provenance data.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 result_extractor: Optional[ResultExtractor] = None):
        """
        Initialize the ResultCapture.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            result_extractor: Optional ResultExtractor instance. If None, a new one is created.
        """
        self.logger = get_logger(__name__)
        self.config_manager = config_manager or ConfigManager()
        self.result_extractor = result_extractor or ResultExtractor()
        self.logger.debug(f"ResultCapture initialized with ConfigManager: {self.config_manager.__class__.__name__}")
        self.logger.debug(f"ResultCapture initialized with ResultExtractor: {self.result_extractor.__class__.__name__}")
        
    def capture_results(self, job_id: str, job_name: str, output_files: List[str], profile_name: str = "") -> Dict[str, Any]:
        """
        Capture and store benchmark results.

        Args:
            job_id: ID of the job.
            job_name: Name of the job.
            output_files: List of output files to process.
            profile_name: Name of the profile used for the benchmark.

        Returns:
            Dictionary with extracted results.
        """
        self.logger.info(f"Capturing results for job {job_id}")

        # Initialize results
        results = {
            "job_id": job_id,
            "job_name": job_name,
            "success": False,
            "metric": None,
            "unit": None,
            "value": None,
            "error": None
        }

        if not output_files:
            self.logger.error("No output files provided")
            results["error"] = "No output files provided"
            return results

        # Check if files exist
        for output_file in output_files:
            if not os.path.isfile(output_file):
                self.logger.error(f"Output file not found: {output_file}")
                results["error"] = f"Output file not found: {output_file}"
                return results

        # Try to load profile configuration
        profile_config = None
        
        # First, check if there's a profile file in the workspace directory
        workspace_dir = os.path.dirname(output_files[0])
        inputs_dir = os.path.join(workspace_dir, "inputs")
        
        # Try to find profile file in the workspace inputs directory
        if os.path.isdir(inputs_dir):
            for filename in os.listdir(inputs_dir):
                if filename.endswith(".yaml") and (profile_name in filename or not profile_name):
                    workspace_profile_path = os.path.join(inputs_dir, filename)
                    self.logger.info(f"Found profile in workspace: {workspace_profile_path}")
                    profile_config = self.config_manager.load_yaml_file(workspace_profile_path)
                    break
        
        # If not found in workspace, try to load from profile name
        if not profile_config and profile_name:
            try:
                profile_config = self.config_manager.load_profile_config(profile_name, "benchmark")
                self.logger.info(f"Loaded profile configuration for {profile_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load profile configuration: {str(e)}")

        # Extract results from output files
        if profile_config:
            # Get extraction configuration from profile
            extraction_config = profile_config.get("results", {}).get("extraction")
            
            if extraction_config:
                self.logger.info(f"Using extraction method: {extraction_config.get('method', 'unknown')}")
                
                # Extract results from each output file
                for output_file in output_files:
                    self.logger.info(f"Processing output file: {output_file}")
                    
                    # Extract results
                    file_results = self.result_extractor.extract_results(output_file, extraction_config)
                    
                    # If extraction was successful, store results
                    if file_results.get("success", False):
                        results.update(file_results)
                        results["success"] = True
                        self.logger.info(f"Result extraction successful: {results.get('metric')} = {results.get('value')} {results.get('unit')}")
                        break
                    else:
                        self.logger.warning(f"Result extraction failed for {output_file}: {file_results.get('error', 'Unknown error')}")
            else:
                self.logger.warning("No extraction configuration found in profile")
                results["error"] = "No extraction configuration found in profile"
        else:
            self.logger.warning(f"No profile configuration found for {profile_name}")
            results["error"] = f"No profile configuration found for {profile_name}"

        # Store results
        results_file = os.path.join(os.path.dirname(output_files[0]), f"{job_name}_results.json")
        try:
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {results_file}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
            results["error"] = f"Failed to save results: {str(e)}"

        return results
    
    def extract_results(self, profile_name: str, log_file: str, results: Dict[str, Any]) -> None:
        """
        Extract metrics from the benchmark output using the ResultExtractor.
        
        Args:
            profile_name: Name of the benchmark profile.
            log_file: Path to the log file.
            results: Results dictionary to update with extracted metrics.
            
        Returns:
            None. Updates the results dictionary in place.
        """
        try:
            # Load the benchmark profile
            config = self.config_manager.load_profile(profile_name, "benchmark")
            
            # Check if extraction configuration exists
            extraction_config = config.get("results", {}).get("extraction")
            if not extraction_config:
                self.logger.warning(f"No extraction configuration found in profile {profile_name}")
                return
            
            self.logger.info(f"Extracting results using method: {extraction_config.get('method', 'unknown')}")
            
            # Extract results
            extraction_results = self.result_extractor.extract_results(log_file, extraction_config)
            
            # Add extracted metrics to results
            if extraction_results.get("success", False):
                self.logger.info(f"Result extraction successful: {extraction_results.get('metric')}")
                results["extracted_metrics"] = extraction_results.get("metric", {})
            else:
                self.logger.warning(f"Result extraction failed: {extraction_results.get('error', 'Unknown error')}")
        
        except Exception as e:
            self.logger.error(f"Error during result extraction: {str(e)}")
    
    def get_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve results for a specific job.
        
        Args:
            job_id: ID of the job.
            
        Returns:
            Dictionary containing the results, or None if not found.
        """
        # Find the results file for the job
        for filename in os.listdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
            if job_id in filename and filename.endswith("_results.json"):
                try:
                    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename), 'r') as f:
                        return json.load(f)
                except Exception as e:
                    self.logger.error(f"Error reading results file {filename}: {str(e)}")
                    return None
        
        self.logger.warning(f"No results found for job {job_id}")
        return None
    
    def list_results(self) -> List[Dict[str, Any]]:
        """
        List all available results.
        
        Returns:
            List of dictionaries containing basic information about each result.
        """
        results_list = []
        
        for filename in os.listdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
            if filename.endswith("_results.json"):
                try:
                    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename), 'r') as f:
                        data = json.load(f)
                        results_list.append({
                            "job_id": data.get("job_id"),
                            "job_name": data.get("job_name"),
                            "capture_time": data.get("capture_time"),
                            "filename": filename,
                            "extracted_metrics": data.get("extracted_metrics", {})
                        })
                except Exception as e:
                    self.logger.error(f"Error reading results file {filename}: {str(e)}")
        
        return results_list 