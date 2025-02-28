"""
Result Capture Module for BenchPRO.

This module handles capturing job output and provenance data.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional, List


class ResultCapture:
    """
    Captures and stores job results and provenance data.
    """
    
    def __init__(self, results_dir: Optional[str] = None):
        """
        Initialize the ResultCapture.
        
        Args:
            results_dir: Directory where results will be stored.
                        If None, uses the default results directory.
        """
        if results_dir is None:
            # Use the default results directory relative to this file
            self.results_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "results", "output"
            )
        else:
            self.results_dir = results_dir
            
        # Ensure the results directory exists
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
    def capture_results(self, job_id: str, job_name: str, 
                        output_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Capture results for a completed job.
        
        Args:
            job_id: ID of the job.
            job_name: Name of the job.
            output_files: Optional list of output files to capture.
            
        Returns:
            Dictionary containing the captured results.
        """
        self.logger.info(f"Capturing results for job {job_id} ({job_name})")
        
        # Create a results dictionary
        results = {
            "job_id": job_id,
            "job_name": job_name,
            "capture_time": datetime.datetime.now().isoformat(),
            "outputs": {}
        }
        
        # Capture output files if provided
        if output_files:
            for output_file in output_files:
                if os.path.exists(output_file):
                    try:
                        with open(output_file, 'r') as f:
                            results["outputs"][os.path.basename(output_file)] = f.read()
                    except Exception as e:
                        self.logger.error(f"Error reading output file {output_file}: {str(e)}")
                else:
                    self.logger.warning(f"Output file not found: {output_file}")
        
        # Save the results to a JSON file
        results_file = os.path.join(self.results_dir, f"{job_name}_{job_id}_results.json")
        try:
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {results_file}")
        except Exception as e:
            self.logger.error(f"Error saving results to {results_file}: {str(e)}")
            
        return results
    
    def get_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve results for a specific job.
        
        Args:
            job_id: ID of the job.
            
        Returns:
            Dictionary containing the results, or None if not found.
        """
        # Find the results file for the job
        for filename in os.listdir(self.results_dir):
            if job_id in filename and filename.endswith("_results.json"):
                try:
                    with open(os.path.join(self.results_dir, filename), 'r') as f:
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
        
        for filename in os.listdir(self.results_dir):
            if filename.endswith("_results.json"):
                try:
                    with open(os.path.join(self.results_dir, filename), 'r') as f:
                        data = json.load(f)
                        results_list.append({
                            "job_id": data.get("job_id"),
                            "job_name": data.get("job_name"),
                            "capture_time": data.get("capture_time"),
                            "filename": filename
                        })
                except Exception as e:
                    self.logger.error(f"Error reading results file {filename}: {str(e)}")
        
        return results_list 