"""
Capture results from benchmark runs.
"""

import click
import os
import json
import glob
from typing import Optional, List
from benchpro.results.result_capture import ResultCapture
from benchpro.utils.logger import get_logger


@click.command(name="capture", help="Capture results from benchmark runs.")
@click.option("--job-id", required=True, help="The job ID to capture results for.")
@click.option("--job-name", help="The name of the job. If not provided, will try to determine from job info file.")
@click.option("--output-file", help="The output file to process. If not provided, will try to find automatically.")
@click.option("--profile", help="The benchmark profile that was used to run the job. If not provided, will try to determine from job info file.")
@click.option("--workspace-dir", help="The workspace directory containing job files. If not provided, will search in benchmark outputs.")
def capture_results(job_id: str, job_name: Optional[str] = None, output_file: Optional[str] = None, 
                   profile: Optional[str] = None, workspace_dir: Optional[str] = None):
    """
    Capture results from a benchmark run.
    
    Args:
        job_id: The job ID.
        job_name: The name of the job (optional if job info file exists).
        output_file: The output file to process (optional if it can be determined).
        profile: The benchmark profile that was used (optional if it can be determined).
        workspace_dir: The workspace directory containing job files (optional if it can be found).
    """
    logger = get_logger(__name__)
    logger.info(f"Capturing results for job {job_id}")
    
    # Try to find job info file if workspace directory is provided or can be found
    job_info = find_job_info(job_id, workspace_dir)
    
    # Use information from job info file if available
    if job_info:
        if not job_name and "job_name" in job_info:
            job_name = job_info["job_name"]
            logger.info(f"Using job name from job info: {job_name}")
            
        if not output_file and "log_file" in job_info:
            output_file = job_info["log_file"]
            logger.info(f"Using log file from job info: {output_file}")
            
        if not profile and "profile_name" in job_info:
            profile = job_info["profile_name"]
            logger.info(f"Using profile from job info: {profile}")
    
    # Check that we have the required information
    if not job_name:
        logger.error("Job name not provided and could not be determined")
        click.echo("Error: Job name not provided and could not be determined from job info")
        return
        
    if not output_file:
        output_file = find_output_file(job_id, job_name, workspace_dir)
        if not output_file:
            logger.error("Output file not provided and could not be found")
            click.echo("Error: Output file not provided and could not be found")
            return
    
    # Check if output file exists
    if not os.path.isfile(output_file):
        logger.error(f"Output file not found: {output_file}")
        click.echo(f"Error: Output file not found: {output_file}")
        return

    # Initialize ResultCapture
    result_capture = ResultCapture()
    
    # Capture results
    results = result_capture.capture_results(job_id, job_name, [output_file], profile)
    
    # Print results
    if results.get("success", False):
        # Get the metric information
        metric = results.get("metric", {})
        metric_name = results.get("metric", "value")
        metric_value = results.get("value", "unknown")
        metric_unit = results.get("unit", "")
        
        # Format and display the results
        click.echo("Results captured successfully:")
        click.echo(f"  Job ID: {job_id}")
        click.echo(f"  Job Name: {job_name}")
        
        if metric_unit:
            click.echo(f"  {metric_name}: {metric_value} {metric_unit}")
        else:
            click.echo(f"  {metric_name}: {metric_value}")
            
        # Show where results were saved
        results_file = os.path.join(os.path.dirname(output_file), f"{job_name}_results.json")
        if os.path.exists(results_file):
            click.echo(f"\nResults saved to: {results_file}")
    else:
        error_msg = results.get('error', 'Unknown error')
        click.echo(f"Failed to capture results: {error_msg}")
        
        # Suggest potential solutions based on the error
        if error_msg and isinstance(error_msg, str):
            if "No extraction configuration found" in error_msg:
                click.echo("\nSuggestion: Check that your benchmark profile includes a 'results.extraction' section.")
                click.echo("Example configuration:")
                click.echo("""
    results:
      extraction:
        method: regex
        pattern: "Result: (\\d+\\.?\\d*)"
        metric: "execution_time"
        unit: "seconds"
                """)
            elif "No profile configuration found" in error_msg:
                click.echo("\nSuggestion: Make sure to specify the correct profile name with --profile option.")
            elif "Output file not found" in error_msg:
                click.echo("\nSuggestion: Check that the output file path is correct and the file exists.")
            elif "Extraction returned no result" in error_msg:
                click.echo("\nSuggestion: Check that the benchmark output contains the expected pattern to extract.")
                click.echo("You may need to modify the extraction configuration in your benchmark profile.")


def find_job_info(job_id: str, workspace_dir: Optional[str] = None) -> Optional[dict]:
    """
    Find the job info file for a given job ID.
    
    Args:
        job_id: The job ID to find info for.
        workspace_dir: Optional directory to look in first.
        
    Returns:
        Job info dictionary if found, None otherwise.
    """
    logger = get_logger(__name__)
    
    # If workspace_dir is provided, look there first
    if workspace_dir and os.path.isdir(workspace_dir):
        # Look for job info files in the workspace directory
        job_info_files = glob.glob(os.path.join(workspace_dir, "*job_info.json"))
        for job_info_file in job_info_files:
            try:
                with open(job_info_file, 'r') as f:
                    job_info = json.load(f)
                    if job_info.get("job_id") == job_id:
                        logger.info(f"Found job info file: {job_info_file}")
                        return job_info
            except Exception as e:
                logger.warning(f"Error reading job info file {job_info_file}: {str(e)}")
    
    # If not found and workspace_dir not provided, search in benchmark outputs
    from benchpro.utils.user_dir import user_dir_manager
    benchmark_output_dir = user_dir_manager.get_path("outputs_benchmark")
    
    # Search in all benchmark workspace directories
    for workspace_dir in glob.glob(os.path.join(benchmark_output_dir, "*")):
        if not os.path.isdir(workspace_dir):
            continue
            
        # Look for job info files in each workspace directory
        job_info_files = glob.glob(os.path.join(workspace_dir, "*job_info.json"))
        for job_info_file in job_info_files:
            try:
                with open(job_info_file, 'r') as f:
                    job_info = json.load(f)
                    if job_info.get("job_id") == job_id:
                        logger.info(f"Found job info file: {job_info_file}")
                        return job_info
            except Exception as e:
                logger.warning(f"Error reading job info file {job_info_file}: {str(e)}")
    
    logger.warning(f"No job info file found for job ID {job_id}")
    return None


def find_output_file(job_id: str, job_name: str, workspace_dir: Optional[str] = None) -> Optional[str]:
    """
    Find the output file for a given job.
    
    Args:
        job_id: The job ID.
        job_name: The job name.
        workspace_dir: Optional directory to look in first.
        
    Returns:
        Path to the output file if found, None otherwise.
    """
    logger = get_logger(__name__)
    
    # If workspace_dir is provided, look there first
    if workspace_dir and os.path.isdir(workspace_dir):
        # Look for the typical log file pattern
        log_files = [
            os.path.join(workspace_dir, f"{job_name}_run.log"),
            os.path.join(workspace_dir, f"{job_name}_{job_id}.log"),
            os.path.join(workspace_dir, f"{job_name}.log")
        ]
        
        for log_file in log_files:
            if os.path.isfile(log_file):
                logger.info(f"Found output file: {log_file}")
                return log_file
    
    # If not found and workspace_dir not provided, search in benchmark outputs
    from benchpro.utils.user_dir import user_dir_manager
    benchmark_output_dir = user_dir_manager.get_path("outputs_benchmark")
    
    # Search in all benchmark workspace directories
    for ws_dir in glob.glob(os.path.join(benchmark_output_dir, "*")):
        if not os.path.isdir(ws_dir):
            continue
            
        # Look for the typical log file pattern
        log_files = [
            os.path.join(ws_dir, f"{job_name}_run.log"),
            os.path.join(ws_dir, f"{job_name}_{job_id}.log"),
            os.path.join(ws_dir, f"{job_name}.log")
        ]
        
        for log_file in log_files:
            if os.path.isfile(log_file):
                logger.info(f"Found output file: {log_file}")
                return log_file
    
    logger.warning(f"No output file found for job ID {job_id}")
    return None 