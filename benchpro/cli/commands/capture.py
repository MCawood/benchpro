"""
Command for capturing job results.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any

import click

from benchpro.config.config_manager import ConfigManager
from benchpro.config.loader import YamlConfigLoader
from benchpro.results.result_capture import ResultCapture
from benchpro.utils.logger import setup_logging
from benchpro.executor.executor import Executor
from benchpro.executor.scheduler import Scheduler


@click.command(name="capture", help="Capture results from a completed job")
@click.option("--job-id", required=True, help="Job ID to capture results from")
@click.option("--profile", default="", help="Name of the profile to use for result extraction")
@click.option("--workspace-dir", help="Path to the job workspace directory")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def capture_results(job_id: str, profile: str, workspace_dir: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Capture benchmark results from a completed job.
    
    Args:
        job_id: ID of the job to capture results from.
        profile: Name of the profile to use for result extraction.
        workspace_dir: Path to the job workspace directory.
        verbose: Whether to enable verbose output.
        
    Returns:
        Dictionary with captured results.
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level=log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Capturing results for job {job_id}")
    
    # If workspace_dir is not provided, try to find it
    if not workspace_dir:
        # Try to find the workspace directory in common locations
        from benchpro.utils.user_dir import user_dir_manager
        
        # Check in benchmark outputs directory
        benchmark_outputs = user_dir_manager.get_path("outputs_benchmark")
        logger.debug(f"Looking for job workspace in {benchmark_outputs}")
        
        # Look for directories that might contain the job
        for dirname in os.listdir(benchmark_outputs):
            potential_workspace = os.path.join(benchmark_outputs, dirname)
            if os.path.isdir(potential_workspace):
                # Check if this directory contains job info with matching ID
                job_info_files = [f for f in os.listdir(potential_workspace) 
                                 if f.endswith("_job_info.json")]
                
                for job_info_file in job_info_files:
                    import json
                    try:
                        with open(os.path.join(potential_workspace, job_info_file), 'r') as f:
                            job_info = json.load(f)
                            if job_info.get("job_id") == job_id:
                                workspace_dir = potential_workspace
                                logger.info(f"Found workspace directory: {workspace_dir}")
                                break
                    except Exception as e:
                        logger.debug(f"Error reading {job_info_file}: {str(e)}")
                
                if workspace_dir:
                    break
    
    if not workspace_dir or not os.path.isdir(workspace_dir):
        logger.error(f"Workspace directory not found for job {job_id}")
        click.echo(f"Error: Workspace directory not found for job {job_id}")
        click.echo("Please specify the workspace directory with --workspace-dir")
        sys.exit(1)
    
    # Get job information from job_info.json if available
    job_info = {}
    job_info_files = [f for f in os.listdir(workspace_dir) if f.endswith("_job_info.json")]
    
    if job_info_files:
        import json
        try:
            with open(os.path.join(workspace_dir, job_info_files[0]), 'r') as f:
                job_info = json.load(f)
                logger.info(f"Found job info: {job_info.get('name', 'Unknown')} (Status: {job_info.get('status', 'Unknown')})")
        except Exception as e:
            logger.warning(f"Error reading job info file: {str(e)}")
    
    # Find output files in the workspace
    output_files = []
    for root, _, files in os.walk(workspace_dir):
        for file in files:
            if file.endswith('.out') or file.endswith('.log'):
                output_files.append(os.path.join(root, file))
    
    if not output_files:
        logger.warning("No output files found in workspace")
        click.echo("Warning: No output files found in workspace")
        if not click.confirm("Do you want to continue?"):
            sys.exit(0)
    
    # Get profile name from job info if not provided
    if not profile and job_info.get('profile'):
        profile = job_info.get('profile')
        logger.info(f"Using profile from job info: {profile}")
    
    # Initialize components
    config_manager = ConfigManager()
    config_loader = YamlConfigLoader()
    result_capture = ResultCapture(config_manager=config_manager, config_loader=config_loader)
    
    # Print debug information
    logger.debug(f"Job ID: {job_id}")
    logger.debug(f"Workspace directory: {workspace_dir}")
    logger.debug(f"Profile name: {profile}")
    logger.debug(f"Output files: {output_files}")
    
    # Capture results
    logger.info("Calling result_capture.capture_results...")
    results = result_capture.capture_results(
        job_id=job_id,
        job_name=job_info.get('name', f"job_{job_id}"),
        output_files=output_files,
        profile_name=profile
    )
    logger.info(f"Results: {results}")
    
    # Display results
    if results.get('success', False):
        metric_info = results.get('metric', {})
        metric_name = metric_info.get('name', 'N/A')
        metric_value = metric_info.get('value', 'N/A')
        metric_unit = metric_info.get('unit', '')
        
        click.echo(f"\nResults captured successfully:")
        click.echo(f"Metric: {metric_name}")
        click.echo(f"Value: {metric_value} {metric_unit}")
        
        # Get the job name from the results
        job_name = results.get('job_name', f"job_{job_id}")
        results_file = os.path.join(workspace_dir, f"{job_name}_results.json")
        click.echo(f"\nResults saved to: {results_file}")
    else:
        click.echo(f"\nFailed to capture results: {results.get('error', 'Unknown error')}")
        if verbose:
            click.echo(f"See logs for more details")
    
    return results 