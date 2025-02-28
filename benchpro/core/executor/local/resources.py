"""Resource management for local task execution.

This module provides resource management functionality for local task execution,
including resource validation and monitoring.
"""

import logging
import psutil
import shutil
from typing import Dict, Any, Union
from pathlib import Path

from benchpro.core.domain import Task, Job
from benchpro.core.executor.base import ResourceError

logger = logging.getLogger(__name__)

class ResourceManager:
    """Manages resources for local task execution.
    
    This class handles:
    - Resource validation
    - Resource monitoring
    - Resource usage reporting
    """
    
    def __init__(self, working_dir: Path) -> None:
        """Initialize the resource manager.
        
        Args:
            working_dir: Working directory for resource checks
        """
        self.working_dir = working_dir
        
    async def validate_resources(self, job: Job) -> bool:
        """Validate that a job can be executed.

        Args:
            job: The job to validate

        Returns:
            bool: True if job can be executed, False otherwise
        """
        try:
            # Basic validation
            if not job.tasks:
                logger.warning("Job has no tasks")
                return False

            # Validate working directory exists
            if not self.working_dir.exists():
                logger.warning("Working directory does not exist: %s", self.working_dir)
                return False

            return True

        except Exception as e:
            logger.error("Error validating resources: %s", str(e))
            return False
            
    async def release_resources(self, task: Task) -> None:
        """Release resources allocated to a task.
        
        This is a no-op for local execution since the OS handles resource cleanup,
        but we log it for tracking purposes.
        
        Args:
            task: The task whose resources should be released
        """
        logger.debug("Releasing resources for task %s", task.name)
            
    def get_resource_usage(self, process: psutil.Process) -> Dict[str, float]:
        """Get resource usage for a process.
        
        Args:
            process: The process to get resource usage for
            
        Returns:
            Dict containing resource usage metrics
        """
        with process.oneshot():
            cpu_percent = process.cpu_percent()
            memory_percent = process.memory_percent()
            memory_info = process.memory_info()
            
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_rss": float(memory_info.rss),
            "memory_vms": float(memory_info.vms)
        } 