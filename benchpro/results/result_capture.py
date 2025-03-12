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
from benchpro.config.loader import YamlConfigLoader
from benchpro.config.interfaces import ConfigLoaderInterface
from benchpro.utils.logger import get_logger


class ResultCapture:
    """
    Captures and stores job results and provenance data.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 result_extractor: Optional[ResultExtractor] = None,
                 config_loader: Optional[ConfigLoaderInterface] = None):
        """
        Initialize the ResultCapture.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            result_extractor: Optional ResultExtractor instance. If None, a new one is created.
            config_loader: Optional ConfigLoaderInterface instance. If None, a new one is created.
        """
        self.logger = get_logger(__name__)
        self.config_manager = config_manager or ConfigManager()
        self.result_extractor = result_extractor or ResultExtractor()
        self.config_loader = config_loader or YamlConfigLoader()
        self.logger.debug(f"ResultCapture initialized with ConfigManager: {self.config_manager.__class__.__name__}")
        self.logger.debug(f"ResultCapture initialized with ResultExtractor: {self.result_extractor.__class__.__name__}")
        self.logger.debug(f"ResultCapture initialized with ConfigLoader: {self.config_loader.__class__.__name__}")
        
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
        self.logger.debug(f"Job name: {job_name}")
        self.logger.debug(f"Output files: {output_files}")
        self.logger.debug(f"Profile name: {profile_name}")

        # Initialize results
        results = {
            "job_id": job_id,
            "job_name": job_name,
            "success": False,
            "metric": None,
            "unit": None,
            "value": None,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Check if we have output files
        if not output_files:
            self.logger.error("No output files provided")
            results["error"] = "No output files provided"
            return results
        
        # Check that at least one output file exists
        valid_files = [f for f in output_files if os.path.isfile(f)]
        if not valid_files:
            self.logger.error(f"None of the provided output files exist: {output_files}")
            results["error"] = f"None of the provided output files exist: {output_files}"
            return results
            
        # Initialize profile configuration
        profile_config = None
        
        # Try to find profile configuration from the workspace
        workspace_dir = os.path.dirname(output_files[0])
        self.logger.debug(f"Looking for profile in workspace directory: {workspace_dir}")
        
        # Try to find profile file in the workspace directory
        if os.path.isdir(workspace_dir):
            for filename in os.listdir(workspace_dir):
                if filename.endswith(".yaml") and (profile_name in filename or not profile_name):
                    workspace_profile_path = os.path.join(workspace_dir, filename)
                    self.logger.info(f"Found profile in workspace: {workspace_profile_path}")
                    try:
                        profile_config = self.config_loader.load_file(workspace_profile_path)
                        self.logger.debug(f"Loaded profile config: {profile_config}")
                    except Exception as e:
                        self.logger.error(f"Error loading profile from {workspace_profile_path}: {str(e)}")
                    break
        
        # If not found in workspace, try to load from profile name
        if not profile_config and profile_name:
            try:
                self.logger.info(f"Trying to load profile config for {profile_name} from config manager")
                profile_config = self.config_manager.load_profile_config(profile_name, "benchmark")
                self.logger.debug(f"Loaded profile config from config manager: {profile_config}")
            except Exception as e:
                self.logger.warning(f"Failed to load profile {profile_name}: {str(e)}")
        
        # If we have a profile config, extract results
        if profile_config:
            # Extract results using the first valid file (assuming it's the log file)
            self.logger.info(f"Extracting results from {valid_files[0]}")
            self.extract_results(profile_name, valid_files[0], results, profile_config)
        else:
            # If no profile config, just store basic info
            self.logger.warning(f"No profile configuration found for {profile_name}")
            results["error"] = f"No profile configuration found for {profile_name}"
        
        # Save results to file
        try:
            results_file = os.path.join(workspace_dir, f"{job_name}_results.json")
            self.logger.info(f"Saving results to {results_file}")
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {results_file}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
            results["error"] = f"Failed to save results: {str(e)}"
        
        return results
    
    def extract_results(self, profile_name: str, log_file: str, results: Dict[str, Any], profile_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Extract metrics from the benchmark output using the ResultExtractor.
        
        Args:
            profile_name: Name of the benchmark profile.
            log_file: Path to the log file.
            results: Results dictionary to update with extracted metrics.
            profile_config: Optional pre-loaded profile configuration.
            
        Returns:
            None. Updates the results dictionary in place.
        """
        try:
            # Load the benchmark profile if not provided
            if not profile_config:
                self.logger.info(f"Loading profile config for {profile_name}")
                profile_config = self.config_manager.load_profile_config(profile_name, task_type="benchmark")
            
            # Check if extraction configuration exists
            extraction_config = profile_config.get("results", {}).get("extraction")
            self.logger.debug(f"Extraction config: {extraction_config}")
            
            if not extraction_config:
                self.logger.warning(f"No extraction configuration found in profile {profile_name}")
                results["error"] = f"No extraction configuration found in profile {profile_name}"
                return
            
            self.logger.info(f"Using extraction method: {extraction_config.get('method', 'default')}")
            
            # Extract metrics from the log file
            self.logger.debug(f"Extracting results from {log_file} with config: {extraction_config}")
            file_results = self.result_extractor.extract_results(log_file, extraction_config)
            self.logger.debug(f"Extraction results: {file_results}")
            
            # Update results with extracted metrics
            if file_results.get("success", False):
                results.update(file_results)
                results["success"] = True
                self.logger.info(f"Result extraction successful: {results.get('metric')} = {results.get('value')} {results.get('unit')}")
            else:
                error_msg = file_results.get("error", "Unknown extraction error")
                self.logger.warning(f"Result extraction failed: {error_msg}")
                results["error"] = error_msg
                
        except Exception as e:
            self.logger.error(f"Error in result extraction: {str(e)}")
            self.logger.exception("Exception details:")
            results["error"] = f"Error in result extraction: {str(e)}"
    
    def get_results(self, job_id: str, workspace_dir: str) -> Dict[str, Any]:
        """
        Get results for a specific job ID.
        
        Args:
            job_id: ID of the job.
            workspace_dir: Directory where job results are stored.
            
        Returns:
            Dictionary with job results.
        """
        results_file = None
        
        # Try to find the results file
        for filename in os.listdir(workspace_dir):
            if filename.endswith("_results.json") and os.path.isfile(os.path.join(workspace_dir, filename)):
                with open(os.path.join(workspace_dir, filename), 'r') as f:
                    try:
                        data = json.load(f)
                        if data.get("job_id") == job_id:
                            results_file = os.path.join(workspace_dir, filename)
                            break
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON in {filename}")
                        continue
        
        if results_file:
            try:
                with open(results_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to read results file {results_file}: {str(e)}")
                return {"error": f"Failed to read results file: {str(e)}"}
        else:
            self.logger.warning(f"No results file found for job {job_id}")
            return {"error": f"No results file found for job {job_id}"}
    
    def list_results(self, workspace_dir: str) -> List[Dict[str, Any]]:
        """
        List all results in the workspace directory.
        
        Args:
            workspace_dir: Directory where job results are stored.
            
        Returns:
            List of dictionaries with job results.
        """
        results = []
        
        # Find all results files
        for filename in os.listdir(workspace_dir):
            if filename.endswith("_results.json") and os.path.isfile(os.path.join(workspace_dir, filename)):
                try:
                    with open(os.path.join(workspace_dir, filename), 'r') as f:
                        data = json.load(f)
                        results.append(data)
                except Exception as e:
                    self.logger.warning(f"Failed to read {filename}: {str(e)}")
                    continue
        
        return results 