"""Build orchestration service."""

import asyncio
import shutil
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional

from benchpro.core.domain.templates.loader import TemplateLoader
from benchpro.core.domain.templates.renderer import TemplateRenderer
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.staging import StagingFile, StagingMode
from benchpro.core.domain.task_registry import TaskRegistry, TaskType
from benchpro.core.executor.local import LocalExecutor
from benchpro.core.services.staging import FileStager
from benchpro.core.services.location_manager import LocationManager
from benchpro.core.services.logging import get_logger
from .build_logger import BuildLogger

logger = get_logger("build")

class BuildError(Exception):
    """Raised when build fails."""
    pass

class BuildOrchestrator:
    """Orchestrates the build process for applications."""
    
    def __init__(
        self,
        template_loader: TemplateLoader,
        executor: LocalExecutor,
        location_manager: LocationManager,
        task_registry: TaskRegistry,
        root_dir: Optional[Path] = None
    ):
        """Initialize build orchestrator.
        
        Args:
            template_loader: Template loader for accessing templates
            executor: Local executor for running build tasks
            location_manager: Manager for task locations
            task_registry: Registry for tracking tasks
            root_dir: Root directory for BenchPRO. Defaults to current directory
        """
        self.template_loader = template_loader
        self.executor = executor
        self.location_manager = location_manager
        self.task_registry = task_registry
        self.root_dir = root_dir or Path.cwd()
        self.file_stager = FileStager()
        logger.debug("Initialized BuildOrchestrator with root_dir=%s", self.root_dir)
    
    def _generate_app_id(self, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Generate a unique ID for an application instance.
        
        The ID is based on:
        - Application name
        - Current timestamp
        - Variables (if any)
        
        Args:
            name: Application name
            variables: Build variables
            
        Returns:
            Unique application ID
        """
        # Create a string containing all inputs
        id_input = f"{name}-{time.time()}"
        if variables:
            # Sort variables to ensure consistent hashing
            var_str = "-".join(f"{k}={v}" for k, v in sorted(variables.items()))
            id_input += f"-{var_str}"
            
        # Generate hash
        hash_obj = hashlib.sha256(id_input.encode())
        app_id = hash_obj.hexdigest()[:12]  # First 12 chars should be sufficient
        logger.debug("Generated app ID %s for %s with variables %s", app_id, name, variables)
        return app_id
    
    async def build_application(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
        custom_location: Optional[Path] = None
    ) -> Path:
        """Build an application from a template.
        
        Args:
            name: Name of the application template
            variables: Optional variables to pass to the template
            custom_location: Optional custom location for the build
            
        Returns:
            Path to the application directory
            
        Raises:
            BuildError: If build fails
        """
        # Generate unique application ID
        app_id = self._generate_app_id(name, variables)
        logger.debug("Starting build for application %s (ID: %s)", name, app_id)
        
        try:
            # Get build location
            build_location = self.location_manager.get_task_location(
                TaskType.BUILD,
                custom_location=custom_location
            )
            self.location_manager.ensure_location(build_location)
            
            # Create application directory
            app_dir = build_location / f"{name}-{app_id}"
            app_dir.mkdir()
            logger.debug("Created application directory: %s", app_dir)
            
            # Create directory structure
            source_dir = app_dir / "source"  # For template files
            build_dir = app_dir / "build"    # For build artifacts
            install_dir = app_dir / "install" # For installed files
            log_dir = app_dir / "logs"       # For build logs
            
            source_dir.mkdir()
            build_dir.mkdir()
            install_dir.mkdir()
            log_dir.mkdir()
            logger.debug("Created directory structure in %s", app_dir)
            
            # Initialize build logger
            logger.debug("Initializing build logger in %s", log_dir)
            build_logger = BuildLogger(log_dir)
            build_logger.log_summary(f"Starting build for {name} (ID: {app_id})")
            if variables:
                build_logger.log_summary(f"Build variables: {variables}")
            
            try:
                # Load template configuration
                logger.debug("Loading template configuration for %s", name)
                config = self.template_loader.load_config(name)
                build_logger.log_summary(f"Loaded template configuration: {config.name} v{config.version}")
                
                # Create task for building
                logger.debug("Creating build task")
                task = Task(
                    name=f"build-{name}-{app_id}",
                    working_dir=build_dir,
                    template_path=None  # Will be set after staging
                )
                
                # Add source files to task for staging
                template_dir = self.template_loader.root_dir
                logger.debug("Template root directory: %s", template_dir)
                if config.source and config.source.files:
                    logger.debug("Source files in config: %s", config.source.files)
                    logger.debug("Adding source files to staging list")
                    for source_file in config.source.files:
                        src_path = template_dir / "applications" / name / source_file
                        logger.debug("Full source path: %s", src_path)
                        logger.debug("Checking if file exists at: %s", src_path)
                        if not src_path.exists():
                            error_msg = f"Source file not found: {src_path}"
                            logger.error(error_msg)
                            raise BuildError(error_msg)
                        dst_path = build_dir / source_file
                        logger.debug("Destination path: %s", dst_path)
                        task.staging_files.append(StagingFile(
                            source=src_path,
                            destination=dst_path,
                            mode=StagingMode.LOCAL_COPY
                        ))
                
                # Load and render build template
                logger.debug("Loading build template")
                build_script = self.template_loader.load_template(name, "build.j2")
                renderer = TemplateRenderer(config, build_script)
                build_logger.log_summary("Loaded build template")
                
                # Create template context with full paths
                logger.debug("Creating template context")
                context = {
                    "working_dir": str(build_dir),
                    "install_dir": str(install_dir),
                    "source_dir": str(source_dir),
                    "build": {
                        "binary": {
                            "directory": config.build.binary.directory,
                            "executable": config.build.binary.executable
                        }
                    }
                }
                if variables:
                    context.update(variables)
                
                rendered_script = renderer.render(context)
                build_logger.log_summary("Rendered build script")
                
                # Write build script to source directory
                logger.debug("Writing build script to %s", source_dir)
                build_script_path = source_dir / "build.sh"
                build_script_path.write_text(rendered_script)
                build_script_path.chmod(0o755)  # Make executable
                build_logger.log_summary("Wrote build script")
                
                # Copy build script to build directory as run.sh
                logger.debug("Copying build script to build directory as run.sh")
                run_script_path = build_dir / "run.sh"
                shutil.copy2(build_script_path, run_script_path)
                run_script_path.chmod(0o755)  # Make executable
                build_logger.log_summary("Copied build script to build directory")
                
                # Set template path in task
                task.template_path = run_script_path
                
                # Create job for the task
                logger.debug("Creating build job")
                job = Job(
                    name=f"build-{name}-{app_id}",
                    working_dir=build_dir,
                    tasks=[task],
                    resources={
                        "cores": 1,
                        "memory": "1G",
                        "walltime": 3600
                    }
                )
                build_logger.log_summary("Created build job")
                
                # Stage files
                logger.debug("Starting file staging")
                await self.file_stager.stage_files(task)
                build_logger.log_summary("Staged source files")
                
                # Execute build
                logger.debug("Submitting build job")
                await self.executor.submit_job(job)
                build_logger.log_summary("Started build execution")
                
                # Monitor build progress
                logger.debug("Monitoring build progress")
                while True:
                    status = await self.executor.get_job_status(job)
                    logger.debug("Job status: %s", status)
                    if status["state"] == "completed":
                        logger.debug("Build completed successfully")
                        build_logger.log_summary("Build completed successfully")
                        break
                    elif status["state"] in ("failed", "cancelled"):
                        error_msg = f"Build failed: {task.error}"
                        logger.error(error_msg)
                        build_logger.log_summary(error_msg, level="ERROR")
                        if build_logger.has_errors():
                            error_context = build_logger.get_error_context()
                            if error_context:
                                build_logger.log_summary("Error context:", level="ERROR")
                                build_logger.log_summary(error_context, level="ERROR")
                        raise BuildError(error_msg)
                    await asyncio.sleep(0.1)
                
                # Register successful build
                self.task_registry.register_task(
                    task_id=app_id,
                    name=name,
                    task_type=TaskType.BUILD,
                    location=app_dir,
                    variables=variables,
                    metadata={
                        "version": str(config.version),
                        "build_time": time.time()
                    }
                )
                
                # Get build summary
                summary = build_logger.get_build_summary()
                build_logger.log_summary(f"Build summary: {summary}")
                logger.debug("Build completed: %s", summary)
                
                return app_dir
                    
            except Exception as e:
                # Log the error
                error_msg = f"Build failed: {str(e)}"
                logger.error(error_msg)
                build_logger.log_summary(error_msg, level="ERROR")
                if isinstance(e, BuildError) and build_logger.has_errors():
                    error_context = build_logger.get_error_context()
                    if error_context:
                        build_logger.log_summary("Error context:", level="ERROR")
                        build_logger.log_summary(error_context, level="ERROR")
                
                # On failure, preserve the directory for debugging but mark it as failed
                (app_dir / "FAILED").touch()
                raise BuildError(error_msg)
                
            finally:
                # Clean up logger
                build_logger.cleanup()
                
        except Exception as e:
            # Handle location-related errors
            error_msg = f"Build failed: {str(e)}"
            logger.error(error_msg)
            raise BuildError(error_msg) 