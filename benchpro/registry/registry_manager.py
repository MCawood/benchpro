"""
Registry Manager for BenchPRO - Database Backend.

This module provides the comprehensive benchmarking knowledge repository 
that serves as the authoritative source of truth for all benchmarking activities.

Key Features:
- Immediate task registration (not completion-based)
- Application vs benchmark differentiation  
- Complete reproducibility metadata storage
- Results storage and analysis capabilities
- Dependency tracking between tasks
- Workspace lifecycle management
"""

import os
import json
import time
import hashlib
import platform
import socket
import shutil
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from benchpro.registry.database_manager import DatabaseManager, DatabaseError
from benchpro.utils.user_dir import get_user_dir_manager
from benchpro.utils.logger import get_logger


class RegistryManager:
    """
    Comprehensive benchmarking knowledge repository with full reproducibility.
    
    This is the authoritative database-backed registry system that supports:
    - Registry as ground truth (not file-dependent)
    - Complete task lifecycle tracking from submission to completion
    - Application and benchmark differentiation
    - Dependency relationships and resolution
    - Results preservation and analysis
    - Full reproducibility through stored metadata
    """
    
    def __init__(self, db_path: Optional[str] = None, 
                 workspace_manager=None):
        """
        Initialize with database path and workspace manager.
        
        Args:
            db_path: Path to database file (None for default)
            workspace_manager: WorkspaceManager instance for integration
        """
        # Setup logging
        if "_BP_COMPLETE" in os.environ:
            import logging
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
        else:
            self.logger = get_logger(__name__)
            self.logger.info("Initializing RegistryManager (Database Backend)")
        
        # Initialize database manager
        self.db = DatabaseManager(db_path)
        
        # Store workspace manager reference
        self.workspace_manager = workspace_manager
        
        # User directory manager
        self.user_dir_manager = get_user_dir_manager()
        
        self.logger.debug(f"RegistryManager initialized with database: {self.db.db_path}")
    
    # ========================================================================
    # Task Lifecycle Management
    # ========================================================================
    
    def register_task_submission(self, task_data: Dict[str, Any], 
                                workspace_dir: str,
                                job_id: Optional[str] = None,
                                system_snapshot: Optional[Dict[str, Any]] = None) -> str:
        """
        Register task immediately upon submission with workspace location.
        
        This is the paradigm shift - tasks are registered when submitted, 
        not when completed. The database becomes the source of truth.
        
        Args:
            task_data: Complete task configuration data
            workspace_dir: Workspace directory path  
            job_id: Optional scheduler job ID
            system_snapshot: System environment data for reproducibility
            
        Returns:
            Task ID
        """
        task_name = task_data.get('name', 'unknown')
        self.logger.info(f"Registering task submission: {task_name}")
        
        # Capture system environment if not provided
        if system_snapshot is None:
            system_snapshot = self._capture_system_environment()
        
        # Store system snapshot and get ID
        system_snapshot_id = self._store_system_snapshot(system_snapshot)
        
        # Prepare complete task data for database
        submission_data = {
            'name': task_data['name'],
            'version': task_data.get('version', '1.0'),
            'task_type': task_data['task_type'],
            'status': 'SUBMITTED',
            'workspace_dir': workspace_dir,
            'workspace_pattern': self._generate_workspace_pattern(workspace_dir),
            'config_snapshot': task_data,  # Complete config for reproducibility
            'system_snapshot_id': system_snapshot_id,
            'template_content': task_data.get('template_content'),
            'cli_overrides': task_data.get('cli_overrides', {}),
            'description': task_data.get('description'),
            'tags': task_data.get('tags', []),
            'workspace_hash': self._calculate_workspace_hash(workspace_dir)
        }
        
        # Insert main task record
        task_id = self.db.insert_task(submission_data)
        
        # Create type-specific entries
        if task_data['task_type'] == 'application':
            self._create_application_entry(task_id, task_data)
        elif task_data['task_type'] == 'benchmark':
            self._create_benchmark_entry(task_id, task_data)
        
        # Update with job ID if provided
        if job_id:
            self.update_task_job_id(task_id, job_id)
        
        self.logger.info(f"Task registered: {task_id} ({task_name})")
        return task_id
    
    def update_task_completion(self, task_id: str, 
                             completion_data: Dict[str, Any]) -> bool:
        """
        Update task completion status and metadata.
        
        Args:
            task_id: Task ID
            completion_data: Completion status and metadata
            
        Returns:
            True if successful
        """
        self.logger.info(f"Updating task completion: {task_id}")
        
        updates = {
            'completion_time': completion_data.get('completion_time', 
                                                 datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')),
            'status': completion_data.get('status', 'COMPLETED')
        }
        
        # Add any additional completion metadata
        for key in ['workspace_hash', 'files_cleaned']:
            if key in completion_data:
                updates[key] = completion_data[key]
        
        success = self.db.update_task(task_id, updates)
        
        if success:
            self.logger.info(f"Task completion updated: {task_id}")
        else:
            self.logger.error(f"Failed to update task completion: {task_id}")
        
        return success
    
    def update_task_job_id(self, task_id: str, job_id: str) -> bool:
        """
        Update task with scheduler job ID after submission.
        
        Args:
            task_id: Task ID
            job_id: Scheduler job ID
            
        Returns:
            True if successful
        """
        # Store job_id in config_snapshot for scheduler integration
        task = self.db.get_task(task_id)
        if not task:
            self.logger.error(f"Task not found for job ID update: {task_id}")
            return False
        
        config = task.get('config_snapshot', {})
        config['job_id'] = job_id
        
        success = self.db.update_task(task_id, {
            'config_snapshot': config,
            'status': 'RUNNING'
        })
        
        if success:
            self.logger.debug(f"Updated job ID for task {task_id}: {job_id}")
        
        return success
    
    # ========================================================================
    # Application-Specific Methods
    # ========================================================================
    
    def register_application_build(self, task_id: str, 
                                 build_data: Dict[str, Any]) -> bool:
        """
        Register application build completion and artifacts.
        
        Args:
            task_id: Application task ID
            build_data: Build completion data and artifacts
            
        Returns:
            True if successful
        """
        self.logger.info(f"Registering application build: {task_id}")
        
        try:
            # Update applications table with build results
            query = """
                UPDATE applications SET 
                    binary_path = ?, build_artifacts = ?, module_file_path = ?,
                    build_config = ?, build_success = ?, build_duration_seconds = ?,
                    build_log_summary = ?
                WHERE task_id = ?
            """
            params = (
                build_data.get('binary_path'),
                json.dumps(build_data.get('build_artifacts', [])),
                build_data.get('module_file_path'),
                json.dumps(build_data.get('build_config', {})),
                build_data.get('build_success', True),
                build_data.get('build_duration_seconds'),
                build_data.get('build_log_summary'),
                task_id
            )
            
            rows_affected = self.db.execute_update(query, params)
            
            if rows_affected > 0:
                # Update main task status
                completion_status = 'COMPLETED' if build_data.get('build_success', True) else 'FAILED'
                self.update_task_completion(task_id, {'status': completion_status})
                
                self.logger.info(f"Application build registered: {task_id}")
                return True
            else:
                self.logger.error(f"Application task not found: {task_id}")
                return False
                
        except DatabaseError as e:
            self.logger.error(f"Failed to register application build: {e}")
            return False
    
    def get_application_binary(self, app_task_id: str) -> Optional[str]:
        """
        Get binary path for application task.
        
        Args:
            app_task_id: Application task ID
            
        Returns:
            Binary path if found, None otherwise
        """
        query = "SELECT binary_path FROM applications WHERE task_id = ?"
        results = self.db.execute_query(query, (app_task_id,))
        
        if results and results[0]['binary_path']:
            return results[0]['binary_path']
        return None
    
    # ========================================================================
    # Benchmark-Specific Methods  
    # ========================================================================
    
    def register_benchmark_results(self, task_id: str,
                                 results_data: Dict[str, Any],
                                 figures_of_merit: Dict[str, Any]) -> bool:
        """
        Store benchmark results and figures of merit.
        
        Args:
            task_id: Benchmark task ID
            results_data: Complete results data
            figures_of_merit: Key performance metrics extracted
            
        Returns:
            True if successful
        """
        self.logger.info(f"Registering benchmark results: {task_id}")
        
        try:
            # Insert or update benchmark_results table
            query = """
                INSERT OR REPLACE INTO benchmark_results 
                (benchmark_id, results_data, figures_of_merit, performance_metrics,
                 output_files_captured, result_extraction_method, results_validated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                task_id,
                json.dumps(results_data),
                json.dumps(figures_of_merit),
                json.dumps(results_data.get('performance_metrics', {})),
                json.dumps(results_data.get('output_files', [])),
                results_data.get('extraction_method', 'automatic'),
                results_data.get('validated', False)
            )
            
            self.db.execute_update(query, params)
            
            # Update main task status to completed
            self.update_task_completion(task_id, {'status': 'COMPLETED'})
            
            self.logger.info(f"Benchmark results registered: {task_id}")
            return True
            
        except DatabaseError as e:
            self.logger.error(f"Failed to register benchmark results: {e}")
            return False
    
    def get_benchmark_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve benchmark results.
        
        Args:
            task_id: Benchmark task ID
            
        Returns:
            Results data dictionary or None if not found
        """
        query = "SELECT * FROM benchmark_results WHERE benchmark_id = ?"
        results = self.db.execute_query(query, (task_id,))
        
        if results:
            row = results[0]
            return {
                'results_data': json.loads(row['results_data'] or '{}'),
                'figures_of_merit': json.loads(row['figures_of_merit'] or '{}'),
                'performance_metrics': json.loads(row['performance_metrics'] or '{}'),
                'output_files': json.loads(row['output_files_captured'] or '[]'),
                'extraction_method': row['result_extraction_method'],
                'validated': row['results_validated'],
                'extracted_at': row['extracted_at']
            }
        return None
    
    # ========================================================================
    # Dependency Management
    # ========================================================================
    
    def add_task_dependency(self, dependent_task_id: str,
                          dependency_task_id: str,
                          dependency_role: str,
                          dependency_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add dependency relationship between tasks.
        
        Args:
            dependent_task_id: Task that has the dependency
            dependency_task_id: Task that is depended upon
            dependency_role: Type of dependency ('build', 'runtime', 'data', 'module')
            dependency_config: Configuration for how dependency is used
            
        Returns:
            True if successful
        """
        try:
            query = """
                INSERT OR REPLACE INTO task_dependencies 
                (dependent_task_id, dependency_task_id, dependency_role,
                 dependency_config, optional)
                VALUES (?, ?, ?, ?, ?)
            """
            params = (
                dependent_task_id, 
                dependency_task_id, 
                dependency_role,
                json.dumps(dependency_config or {}),
                dependency_config.get('optional', False) if dependency_config else False
            )
            
            self.db.execute_update(query, params)
            self.logger.debug(f"Added dependency: {dependent_task_id} -> {dependency_task_id} ({dependency_role})")
            return True
            
        except DatabaseError as e:
            self.logger.error(f"Failed to add dependency: {e}")
            return False
    
    def resolve_dependencies(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all dependencies for a task with current status.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of dependency information with current status
        """
        query = """
            SELECT td.*, t.name, t.status, t.task_type, 
                   a.binary_path, a.module_file_path
            FROM task_dependencies td
            LEFT JOIN tasks t ON td.dependency_task_id = t.id  
            LEFT JOIN applications a ON td.dependency_task_id = a.task_id
            WHERE td.dependent_task_id = ?
            ORDER BY td.execution_order, td.dependency_role
        """
        
        results = self.db.execute_query(query, (task_id,))
        
        dependencies = []
        for row in results:
            dep_config = json.loads(row['dependency_config'] or '{}')
            dependencies.append({
                'task_id': row['dependency_task_id'],
                'name': row['name'],
                'role': row['dependency_role'],
                'status': row['status'],
                'task_type': row['task_type'],
                'binary_path': row['binary_path'],
                'module_file_path': row['module_file_path'],
                'config': dep_config,
                'optional': row['optional']
            })
        
        return dependencies
    
    # ========================================================================
    # Status and Queries
    # ========================================================================
    
    def get_task_status(self, task_id: str, force_refresh: bool = False) -> str:
        """
        Get current task status with optional scheduler integration.
        
        Args:
            task_id: Task ID
            force_refresh: Whether to check with scheduler for current status
            
        Returns:
            Current status string or "NOT_FOUND"
        """
        task = self.db.get_task(task_id)
        if not task:
            return "NOT_FOUND"
        
        current_status = task['status']
        
        # TODO: Future enhancement - integrate with scheduler for live status
        if force_refresh and current_status in ['SUBMITTED', 'RUNNING']:
            # Could check with Slurm/PBS/etc here for job status
            pass
        
        return current_status
    
    def find_tasks(self, criteria: Dict[str, Any], 
                  include_states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Find tasks with complex criteria and status filtering.
        
        Args:
            criteria: Search criteria dictionary
            include_states: List of statuses to include (None for all)
            
        Returns:
            List of matching task dictionaries
        """
        search_criteria = criteria.copy()
        
        # Add status filtering if specified
        if include_states:
            if len(include_states) == 1:
                search_criteria['status'] = include_states[0]
            else:
                # For multiple states, we'd need to modify the database query
                # For now, just use the first one
                search_criteria['status'] = include_states[0]
        
        return self.db.find_tasks(search_criteria)
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete task information.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task information dictionary or None if not found
        """
        return self.db.get_task(task_id)
    
    def find_task_by_job_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Find task by job ID.
        
        Args:
            job_id: Job ID to search for
            
        Returns:
            Task information dictionary or None if not found
        """
        # Use the existing find_tasks method to search by job_id
        results = self.find_tasks({'job_id': job_id})
        return results[0] if results else None
    
    def list_applications(self, status_filter: str = "COMPLETED") -> List[Dict[str, Any]]:
        """
        List applications with optional status filtering.
        
        Args:
            status_filter: Status to filter by (None for all)
            
        Returns:
            List of application task dictionaries
        """
        criteria = {'task_type': 'application'}
        if status_filter:
            criteria['status'] = status_filter
        
        return self.find_tasks(criteria)
    
    def list_benchmarks(self, has_results: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        List benchmarks with optional result filtering.
        
        Args:
            has_results: Filter by whether benchmark has results stored
            
        Returns:
            List of benchmark task dictionaries
        """
        if has_results is True:
            # Find benchmarks that have results
            query = """
                SELECT t.* FROM tasks t
                INNER JOIN benchmark_results br ON t.id = br.benchmark_id
                WHERE t.task_type = 'benchmark'
                ORDER BY t.submission_time DESC
            """
            results = self.db.execute_query(query)
            return [self.db._row_to_dict(row) for row in results]
        elif has_results is False:
            # Find benchmarks without results
            query = """
                SELECT t.* FROM tasks t
                LEFT JOIN benchmark_results br ON t.id = br.benchmark_id
                WHERE t.task_type = 'benchmark' AND br.benchmark_id IS NULL
                ORDER BY t.submission_time DESC
            """
            results = self.db.execute_query(query)
            return [self.db._row_to_dict(row) for row in results]
        else:
            # All benchmarks
            return self.find_tasks({'task_type': 'benchmark'})
    
    # ========================================================================
    # Reproducibility and Rerun
    # ========================================================================
    
    def rerun_task(self, original_task_id: str,
                  config_overrides: Optional[Dict[str, Any]] = None,
                  reason: Optional[str] = None) -> str:
        """
        Create new task identical to original for rerun.
        
        This enables exact reproduction of previous tasks with optional
        configuration changes for comparison studies.
        
        Args:
            original_task_id: Original task ID to replicate
            config_overrides: Optional configuration changes
            reason: Reason for rerun (for tracking)
            
        Returns:
            New task ID for the rerun
        """
        self.logger.info(f"Creating rerun for task: {original_task_id}")
        
        original_task = self.db.get_task(original_task_id)
        if not original_task:
            raise ValueError(f"Original task not found: {original_task_id}")
        
        # Create new configuration with overrides
        new_config = original_task['config_snapshot'].copy()
        if config_overrides:
            new_config.update(config_overrides)
        
        # Create new workspace through workspace manager if available
        if self.workspace_manager:
            new_workspace = self.workspace_manager.create_workspace(
                new_config['name'],
                new_config.get('version', '1.0'),
                new_config['task_type']
            )
        else:
            # Fallback - generate new workspace path pattern
            timestamp = int(time.time())
            original_workspace = Path(original_task['workspace_dir'])
            new_workspace = f"{original_workspace.parent}/{original_workspace.stem}_rerun_{timestamp}"
        
        # Register new task for rerun
        new_task_id = self.register_task_submission(
            task_data=new_config,
            workspace_dir=new_workspace
        )
        
        # Record rerun history for tracking and analysis
        try:
            query = """
                INSERT INTO rerun_history 
                (original_task_id, new_task_id, rerun_reason, config_differences)
                VALUES (?, ?, ?, ?)
            """
            params = (
                original_task_id, 
                new_task_id, 
                reason or "User requested rerun",
                json.dumps(config_overrides or {})
            )
            self.db.execute_update(query, params)
        except DatabaseError:
            self.logger.warning("Failed to record rerun history")
        
        self.logger.info(f"Rerun task created: {new_task_id}")
        return new_task_id
    
    def recreate_task_config(self, task_id: str) -> Dict[str, Any]:
        """
        Recreate complete configuration for task reproduction.
        
        Args:
            task_id: Task ID
            
        Returns:
            Complete configuration dictionary for exact reproduction
        """
        task = self.db.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        return task['config_snapshot']
    
    # ========================================================================
    # Historical Analysis
    # ========================================================================
    
    def compare_benchmark_results(self, task_id1: str, task_id2: str) -> Dict[str, Any]:
        """
        Compare results between two benchmark tasks.
        
        Args:
            task_id1: First benchmark task ID
            task_id2: Second benchmark task ID
            
        Returns:
            Comparison results dictionary
        """
        try:
            # Get results for both tasks
            results1 = self.get_benchmark_results(task_id1)
            results2 = self.get_benchmark_results(task_id2)
            
            if not results1:
                return {"error": f"No results found for task {task_id1}"}
            
            if not results2:
                return {"error": f"No results found for task {task_id2}"}
            
            # Compare figures of merit
            comparison = {
                "task_id1": task_id1,
                "task_id2": task_id2,
                "metrics_comparison": {},
                "performance_delta": {},
                "comparison_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            
            fom1 = results1.get("figures_of_merit", {})
            fom2 = results2.get("figures_of_merit", {})
            
            # Compare common metrics
            common_metrics = set(fom1.keys()) & set(fom2.keys())
            
            for metric in common_metrics:
                val1 = fom1[metric]
                val2 = fom2[metric]
                
                try:
                    val1_num = float(val1)
                    val2_num = float(val2)
                    delta = val2_num - val1_num
                    percent_change = (delta / val1_num * 100) if val1_num != 0 else 0
                    
                    comparison["metrics_comparison"][metric] = {
                        "task1_value": val1,
                        "task2_value": val2,
                        "absolute_delta": delta,
                        "percent_change": percent_change
                    }
                except (ValueError, TypeError):
                    comparison["metrics_comparison"][metric] = {
                        "task1_value": val1,
                        "task2_value": val2,
                        "note": "Non-numeric values, cannot calculate delta"
                    }
            
            return comparison
            
        except DatabaseError as e:
            self.logger.error(f"Database error comparing results: {e}")
            return {"error": str(e)}
        except Exception as e:
            self.logger.error(f"Error comparing benchmark results: {e}")
            return {"error": str(e)}
    
    def get_performance_trends(self, benchmark_name: str,
                             metric: str,
                             time_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict[str, Any]]:
        """
        Analyze performance trends over time for a specific benchmark and metric.
        
        Args:
            benchmark_name: Name of the benchmark
            metric: Performance metric to analyze
            time_range: Optional time range tuple (start, end)
            
        Returns:
            List of performance data points over time
        """
        try:
            # Build query criteria
            criteria = {
                "name": benchmark_name,
                "task_type": "benchmark"
            }
            
            if time_range:
                criteria["since"] = time_range[0].isoformat()
                criteria["until"] = time_range[1].isoformat()
            
            # Get matching benchmark tasks
            benchmark_tasks = self.find_tasks(criteria)
            
            # Extract performance data points
            trend_data = []
            
            for task in benchmark_tasks:
                task_id = task["id"]
                results = self.get_benchmark_results(task_id)
                
                if results and "figures_of_merit" in results:
                    fom = results["figures_of_merit"]
                    if metric in fom:
                        try:
                            value = float(fom[metric])
                            trend_data.append({
                                "task_id": task_id,
                                "timestamp": task["submission_time"],
                                "metric": metric,
                                "value": value,
                                "benchmark_name": benchmark_name,
                                "version": task.get("version", "unknown")
                            })
                        except (ValueError, TypeError):
                            # Skip non-numeric values
                            continue
            
            # Sort by timestamp
            trend_data.sort(key=lambda x: x["timestamp"])
            
            return trend_data
            
        except DatabaseError as e:
            self.logger.error(f"Database error analyzing trends: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error analyzing performance trends: {e}")
            return []
    
    # ========================================================================
    # Workspace Validation and Maintenance
    # ========================================================================
    
    def validate_task_workspace(self, task_id: str) -> Tuple[bool, List[str]]:
        """
        Validate workspace files against database state using WorkspaceManager.
        
        Args:
            task_id: Task ID to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        self.logger.info(f"Validating workspace for task: {task_id}")
        
        try:
            # Get task from database
            task = self.db.get_task(task_id)
            if not task:
                return False, [f"Task not found: {task_id}"]
            
            workspace_dir = task.get("workspace_dir")
            if not workspace_dir:
                return False, ["No workspace directory recorded for task"]
            
            # Use WorkspaceManager for validation
            if self.workspace_manager:
                is_valid, issues = self.workspace_manager.validate_workspace_integrity(workspace_dir)
                
                # Add additional registry-specific validation
                if task.get("files_cleaned"):
                    issues.append("Task workspace marked as cleaned in database")
                
                return is_valid, issues
            else:
                # Fallback validation without WorkspaceManager
                if not os.path.exists(workspace_dir):
                    return False, ["Workspace directory does not exist"]
                
                return True, []
                
        except Exception as e:
            self.logger.error(f"Error validating workspace: {e}")
            return False, [f"Validation error: {e}"]
    
    def cleanup_orphaned_workspaces(self, dry_run: bool = True) -> List[str]:
        """
        Clean up workspace directories with no database entry.
        
        Args:
            dry_run: If True, only report what would be cleaned
            
        Returns:
            List of workspace directories that were/would be cleaned
        """
        self.logger.info(f"Scanning for orphaned workspaces (dry_run={dry_run})")
        
        orphaned_workspaces = []
        
        try:
            # Get all tasks from database with workspace directories
            all_tasks = self.db.find_tasks({})
            registered_workspaces = set()
            
            for task in all_tasks:
                workspace_dir = task.get("workspace_dir")
                if workspace_dir and os.path.exists(workspace_dir):
                    registered_workspaces.add(workspace_dir)
            
            # Scan application and benchmark output directories
            app_output_dir = self.user_dir_manager.get_application_directory()
            bench_output_dir = self.user_dir_manager.get_benchmark_directory()
            
            for output_dir in [app_output_dir, bench_output_dir]:
                if not os.path.exists(output_dir):
                    continue
                
                for item in os.listdir(output_dir):
                    workspace_path = os.path.join(output_dir, item)
                    
                    # Check if it looks like a workspace directory
                    if (os.path.isdir(workspace_path) and 
                        workspace_path not in registered_workspaces and
                        self._looks_like_workspace(workspace_path)):
                        
                        orphaned_workspaces.append(workspace_path)
                        
                        if not dry_run:
                            try:
                                if self.workspace_manager:
                                    # Mark as cleaned before removing
                                    self.workspace_manager.mark_workspace_cleaned(
                                        workspace_path, 
                                        cleanup_reason="Orphaned workspace cleanup"
                                    )
                                
                                shutil.rmtree(workspace_path)
                                self.logger.info(f"Cleaned orphaned workspace: {workspace_path}")
                            except Exception as e:
                                self.logger.warning(f"Could not clean {workspace_path}: {e}")
            
            if dry_run and orphaned_workspaces:
                self.logger.info(f"Found {len(orphaned_workspaces)} orphaned workspaces (dry run)")
            elif orphaned_workspaces:
                self.logger.info(f"Cleaned {len(orphaned_workspaces)} orphaned workspaces")
            
            return orphaned_workspaces
            
        except Exception as e:
            self.logger.error(f"Error cleaning orphaned workspaces: {e}")
            return []
    
    def mark_workspace_cleaned(self, task_id: str) -> bool:
        """
        Mark task workspace as deliberately cleaned.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if successful
        """
        try:
            # Update database record
            success = self.db.update_task(task_id, {"files_cleaned": True})
            
            if success:
                # Also mark in workspace if it exists
                task = self.db.get_task(task_id)
                if task and task.get("workspace_dir") and self.workspace_manager:
                    workspace_dir = task["workspace_dir"]
                    if os.path.exists(workspace_dir):
                        try:
                            self.workspace_manager.mark_workspace_cleaned(
                                workspace_dir, 
                                cleanup_reason="Marked via registry"
                            )
                        except Exception as e:
                            self.logger.warning(f"Could not mark workspace as cleaned: {e}")
                
                self.logger.info(f"Marked task {task_id} workspace as cleaned")
            
            return success
            
        except DatabaseError as e:
            self.logger.error(f"Error marking workspace as cleaned: {e}")
            return False
    
    def get_workspace_info(self, task_id: str) -> Dict[str, Any]:
        """
        Get comprehensive workspace information for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dictionary containing workspace information
        """
        try:
            # Get task from database
            task = self.db.get_task(task_id)
            if not task:
                return {"error": f"Task not found: {task_id}"}
            
            workspace_dir = task.get("workspace_dir")
            if not workspace_dir:
                return {"error": "No workspace directory recorded for task"}
            
            # Get workspace info from WorkspaceManager if available
            if self.workspace_manager:
                workspace_info = self.workspace_manager.get_workspace_info(workspace_dir)
            else:
                # Basic info without WorkspaceManager
                workspace_info = {
                    "workspace_dir": workspace_dir,
                    "exists": os.path.exists(workspace_dir),
                    "registry_cleaned": task.get("files_cleaned", False)
                }
            
            # Add registry-specific information
            workspace_info.update({
                "task_id": task_id,
                "task_name": task.get("name"),
                "task_type": task.get("task_type"),
                "registry_cleaned": task.get("files_cleaned", False),
                "workspace_pattern": task.get("workspace_pattern"),
                "submission_time": task.get("submission_time"),
                "completion_time": task.get("completion_time"),
                "status": task.get("status")
            })
            
            return workspace_info
            
        except Exception as e:
            self.logger.error(f"Error getting workspace info: {e}")
            return {"error": str(e)}
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _create_application_entry(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Create initial application-specific database entry."""
        query = "INSERT INTO applications (task_id) VALUES (?)"
        self.db.execute_update(query, (task_id,))
    
    def _create_benchmark_entry(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Create initial benchmark-specific database entry."""
        has_deps = len(task_data.get('dependencies', [])) > 0
        
        query = """
            INSERT INTO benchmarks (task_id, execution_config, has_application_dependencies) 
            VALUES (?, ?, ?)
        """
        params = (
            task_id, 
            json.dumps(task_data.get('execution', {})), 
            has_deps
        )
        self.db.execute_update(query, params)
    
    def _capture_system_environment(self) -> Dict[str, Any]:
        """Capture current system environment for reproducibility."""
        return {
            'hostname': socket.gethostname(),
            'os_info': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'python_version': platform.python_version(),
            'environment_vars': dict(os.environ),
            'captured_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    
    def _store_system_snapshot(self, snapshot: Dict[str, Any]) -> str:
        """Store system snapshot and return unique ID."""
        # Create deterministic ID from snapshot content
        snapshot_content = json.dumps(snapshot, sort_keys=True)
        snapshot_id = hashlib.md5(snapshot_content.encode()).hexdigest()
        
        try:
            query = """
                INSERT OR IGNORE INTO system_environments 
                (id, hostname, os_info, environment_vars)
                VALUES (?, ?, ?, ?)
            """
            params = (
                snapshot_id,
                snapshot['hostname'],
                json.dumps(snapshot.get('os_info', {})),
                json.dumps(snapshot.get('environment_vars', {}))
            )
            self.db.execute_update(query, params)
        except DatabaseError:
            self.logger.warning("Failed to store system snapshot")
        
        return snapshot_id
    
    def _generate_workspace_pattern(self, workspace_dir: str) -> str:
        """Generate workspace pattern for recreation."""
        path = Path(workspace_dir)
        return f"{path.parent}/{path.stem}_*"
    
    def _calculate_workspace_hash(self, workspace_dir: str) -> str:
        """Calculate hash of workspace for change detection."""
        # Simple hash based on directory path for now
        # Future: could hash actual file contents
        return hashlib.md5(workspace_dir.encode()).hexdigest()[:16]
    
    def _looks_like_workspace(self, workspace_dir: str) -> bool:
        """Check if a directory looks like a workspace."""
        # This is a placeholder implementation. You might want to
        # implement a more robust check based on your workspace naming convention
        # or by checking for the presence of common workspace files or directories.
        return os.path.exists(workspace_dir) and os.path.isdir(workspace_dir) 