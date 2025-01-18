"""File staging service."""

import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict
import os

from benchpro.core.domain.staging import StagingMode, StagingFile
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.services.logging import get_logger
from benchpro.core.domain.errors import StagingError

logger = get_logger("staging")

class FileStager:
    """Service for staging files asynchronously."""
    
    def __init__(self, max_concurrent: Optional[int] = None):
        """Initialize the file stager.
        
        Args:
            max_concurrent: Maximum number of concurrent staging operations.
                          Defaults to 2 if not specified.
        """
        self._semaphore = asyncio.Semaphore(max_concurrent or 2)
        self._staging_tasks = {}
        logger.debug("Initialized FileStager with max_concurrent=%s", max_concurrent or 2)

    async def stage_files(self, task: Task) -> None:
        """Stage all files for a task.
        
        Args:
            task: Task containing files to stage
            
        Raises:
            StagingError: If staging fails
        """
        if not task.staging_files:
            logger.debug("Task %s: No files to stage", task.id)
            return
            
        logger.debug("Task %s: Starting staging for %d files", task.id, len(task.staging_files))
        
        try:
            # Create staging tasks for each file
            staging_ops = []
            for staging_file in task.staging_files:
                if staging_file.needs_staging():
                    logger.debug("Task %s: Queueing staging operation: %s -> %s (mode: %s)", 
                               task.id, staging_file.source, staging_file.destination, staging_file.mode)
                    staging_ops.append(self._stage_file(task, staging_file))
                else:
                    logger.debug("Task %s: Skipping file that doesn't need staging: %s", 
                               task.id, staging_file.source)
            
            # Wait for all staging operations to complete
            if staging_ops:
                logger.debug("Task %s: Waiting for %d staging operations to complete", task.id, len(staging_ops))
                await asyncio.gather(*staging_ops)
                logger.debug("Task %s: All staging operations completed successfully", task.id)
            
            logger.debug("Task %s: Staging completed", task.id)
            
        except Exception as e:
            error_msg = f"Staging failed: {str(e)}"
            logger.error("Task %s: %s", task.id, error_msg)
            raise StagingError(error_msg)

    async def _stage_file(self, task: Task, staging_file: StagingFile) -> None:
        """Stage a single file.
        
        Args:
            task: Task that owns the file
            staging_file: File to stage
            
        Raises:
            StagingError: If staging fails
        """
        async with self._semaphore:
            try:
                logger.debug("Task %s: Staging file %s -> %s (mode: %s)", 
                           task.id, staging_file.source, staging_file.destination, staging_file.mode)
                
                # Skip if source and destination are exactly the same path
                if str(staging_file.source) == str(staging_file.destination):
                    logger.debug("Task %s: Source and destination are the same path, skipping: %s", 
                               task.id, staging_file.source)
                    return
                
                # Create parent directories
                staging_file.destination.parent.mkdir(parents=True, exist_ok=True)
                logger.debug("Task %s: Created parent directory: %s", 
                           task.id, staging_file.destination.parent)
                
                if staging_file.mode == StagingMode.LOCAL_COPY:
                    # Copy the file
                    logger.debug("Task %s: Copying file %s -> %s", 
                               task.id, staging_file.source, staging_file.destination)
                    shutil.copy2(staging_file.source, staging_file.destination)
                    logger.debug("Task %s: File copy completed successfully", task.id)
                elif staging_file.mode == StagingMode.SYMLINK:
                    # Create symlink
                    logger.debug("Task %s: Creating symlink %s -> %s", 
                               task.id, staging_file.source, staging_file.destination)
                    staging_file.destination.symlink_to(staging_file.source)
                    logger.debug("Task %s: Symlink created successfully", task.id)
                else:
                    logger.error("Task %s: Unsupported staging mode: %s", task.id, staging_file.mode)
                    raise StagingError(f"Unsupported staging mode: {staging_file.mode}")

            except Exception as e:
                error_msg = f"Failed to stage {staging_file.source}: {str(e)}"
                logger.error("Task %s: %s", task.id, error_msg)
                raise StagingError(error_msg)

    async def _copy_file(self, src: Path, dst: Path) -> None:
        """Copy a file asynchronously.
        
        This is a placeholder for future optimization. Currently uses shutil.copy2
        but could be enhanced to use aiofiles or other async I/O methods.
        
        Args:
            src: Source path
            dst: Destination path
        """
        logger.debug("Copying file %s -> %s", src, dst)
        shutil.copy2(src, dst)
        logger.debug("File copy completed successfully") 