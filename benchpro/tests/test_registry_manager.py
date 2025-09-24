"""
Unit tests for RegistryManager V2 (Database Backend).

Tests the comprehensive benchmarking knowledge repository functionality
including task lifecycle, reproducibility, dependency management, and analysis.
"""

import os
import tempfile
import unittest
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from benchpro.registry.registry_manager import RegistryManager
from benchpro.registry.database_manager import DatabaseError


class TestRegistryManagerV2(unittest.TestCase):
    """Test cases for RegistryManager V2."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_registry.db")
        
        # Create test database with schema
        self._create_test_database()
        
        # Mock workspace manager
        self.mock_workspace_manager = MagicMock()
        
        # Initialize registry manager
        self.registry = RegistryManager(
            db_path=self.test_db_path,
            workspace_manager=self.mock_workspace_manager
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up database connections
        if hasattr(self, 'registry'):
            self.registry.db.cleanup_connections()
        
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_database(self):
        """Create test database with proper schema."""
        import subprocess
        result = subprocess.run([
            'python3', 'scripts/setup_database.py', 
            '--db-path', self.test_db_path
        ], capture_output=True, text=True)
        
        # If setup script fails, create minimal schema
        if result.returncode != 0:
            self._create_minimal_schema()
    
    def _create_minimal_schema(self):
        """Create minimal database schema for testing."""
        import sqlite3
        conn = sqlite3.connect(self.test_db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        
        conn.executescript("""
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                task_type TEXT NOT NULL CHECK (task_type IN ('application', 'benchmark')),
                submission_time DATETIME NOT NULL,
                completion_time DATETIME,
                status TEXT NOT NULL,
                workspace_dir TEXT,
                workspace_pattern TEXT,
                files_cleaned BOOLEAN DEFAULT FALSE,
                config_snapshot TEXT NOT NULL,
                system_snapshot_id TEXT,
                template_content TEXT,
                cli_overrides TEXT,
                description TEXT,
                tags TEXT,
                ingest_source TEXT DEFAULT 'benchpro_generated',
                workspace_hash TEXT,
                metadata_version TEXT DEFAULT '1.0',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE applications (
                task_id TEXT PRIMARY KEY,
                binary_path TEXT,
                build_artifacts TEXT,
                module_file_path TEXT,
                build_config TEXT,
                build_success BOOLEAN DEFAULT FALSE,
                build_duration_seconds INTEGER,
                build_log_summary TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
            
            CREATE TABLE benchmarks (
                task_id TEXT PRIMARY KEY,
                execution_config TEXT,
                input_specification TEXT,
                has_application_dependencies BOOLEAN DEFAULT FALSE,
                execution_duration_seconds INTEGER,
                execution_log_summary TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
            
            CREATE TABLE benchmark_results (
                benchmark_id TEXT PRIMARY KEY,
                results_data TEXT,
                figures_of_merit TEXT,
                performance_metrics TEXT,
                output_files_captured TEXT,
                result_extraction_method TEXT,
                results_validated BOOLEAN DEFAULT FALSE,
                validation_notes TEXT,
                extracted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (benchmark_id) REFERENCES benchmarks(task_id)
            );
            
            CREATE TABLE task_dependencies (
                dependent_task_id TEXT NOT NULL,
                dependency_task_id TEXT NOT NULL,
                dependency_role TEXT NOT NULL,
                dependency_name TEXT,
                optional BOOLEAN DEFAULT FALSE,
                dependency_config TEXT,
                binary_path_used TEXT,
                module_loaded TEXT,
                execution_order INTEGER,
                version_constraint TEXT,
                PRIMARY KEY (dependent_task_id, dependency_task_id, dependency_role),
                FOREIGN KEY (dependent_task_id) REFERENCES tasks(id),
                FOREIGN KEY (dependency_task_id) REFERENCES tasks(id)
            );
            
            CREATE TABLE system_environments (
                id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                modules_available TEXT,
                module_paths TEXT,
                os_info TEXT,
                hardware_info TEXT,
                compiler_info TEXT,
                environment_vars TEXT,
                captured_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE rerun_history (
                id TEXT PRIMARY KEY,
                original_task_id TEXT NOT NULL,
                new_task_id TEXT NOT NULL,
                rerun_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                rerun_reason TEXT,
                config_differences TEXT,
                result_comparison TEXT,
                reproducibility_verified BOOLEAN,
                FOREIGN KEY (original_task_id) REFERENCES tasks(id),
                FOREIGN KEY (new_task_id) REFERENCES tasks(id)
            );
        """)
        conn.commit()
        conn.close()
    
    # ========================================================================
    # Task Lifecycle Management Tests
    # ========================================================================
    
    def test_register_task_submission(self):
        """Test immediate task registration upon submission."""
        task_data = {
            'name': 'test_application',
            'version': '1.0',
            'task_type': 'application',
            'description': 'Test application for unit tests',
            'tags': ['test', 'application'],
            'config': {
                'compiler': 'gcc',
                'flags': '-O2'
            }
        }
        
        workspace_dir = '/tmp/test_workspace'
        
        task_id = self.registry.register_task_submission(
            task_data=task_data,
            workspace_dir=workspace_dir,
            job_id='test_job_123'
        )
        
        # Verify task was registered
        self.assertIsNotNone(task_id)
        self.assertTrue(task_id.startswith('test_application_10_'))
        
        # Verify task details in database
        task = self.registry.db.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task['name'], 'test_application')
        self.assertEqual(task['version'], '1.0')
        self.assertEqual(task['task_type'], 'application')
        self.assertEqual(task['status'], 'RUNNING')  # RUNNING because job_id was provided
        self.assertEqual(task['workspace_dir'], workspace_dir)
        
        # Verify config snapshot preservation
        self.assertIsInstance(task['config_snapshot'], dict)
        self.assertEqual(task['config_snapshot']['name'], 'test_application')
        
        # Verify application entry was created
        app_binary = self.registry.get_application_binary(task_id)
        # Should be None initially (build not registered yet)
        self.assertIsNone(app_binary)
    
    def test_register_benchmark_submission(self):
        """Test benchmark task registration."""
        task_data = {
            'name': 'test_benchmark',
            'version': '2.0',
            'task_type': 'benchmark',
            'description': 'Test benchmark',
            'dependencies': ['app_task_1'],
            'execution': {
                'input_size': 1000,
                'iterations': 10
            }
        }
        
        task_id = self.registry.register_task_submission(
            task_data=task_data,
            workspace_dir='/tmp/benchmark_workspace'
        )
        
        # Verify benchmark-specific entry
        query = "SELECT * FROM benchmarks WHERE task_id = ?"
        results = self.registry.db.execute_query(query, (task_id,))
        self.assertEqual(len(results), 1)
        
        benchmark = results[0]
        self.assertTrue(benchmark['has_application_dependencies'])
        
        execution_config = json.loads(benchmark['execution_config'])
        self.assertEqual(execution_config['input_size'], 1000)
    
    def test_update_task_completion(self):
        """Test task completion updates."""
        # Register initial task
        task_data = {
            'name': 'completion_test',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        
        task_id = self.registry.register_task_submission(
            task_data=task_data,
            workspace_dir='/tmp/completion_test'
        )
        
        # Update completion
        completion_data = {
            'status': 'COMPLETED',
            'completion_time': '2024-01-01T12:00:00Z',
            'workspace_hash': 'updated_hash'
        }
        
        success = self.registry.update_task_completion(task_id, completion_data)
        self.assertTrue(success)
        
        # Verify updates
        task = self.registry.db.get_task(task_id)
        self.assertEqual(task['status'], 'COMPLETED')
        self.assertEqual(task['completion_time'], '2024-01-01T12:00:00Z')
        self.assertEqual(task['workspace_hash'], 'updated_hash')
    
    def test_update_task_job_id(self):
        """Test job ID updates."""
        task_data = {
            'name': 'job_id_test',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        
        task_id = self.registry.register_task_submission(
            task_data=task_data,
            workspace_dir='/tmp/job_test'
        )
        
        # Update job ID
        success = self.registry.update_task_job_id(task_id, 'slurm_12345')
        self.assertTrue(success)
        
        # Verify job ID stored in config
        task = self.registry.db.get_task(task_id)
        self.assertEqual(task['config_snapshot']['job_id'], 'slurm_12345')
        self.assertEqual(task['status'], 'RUNNING')
    
    # ========================================================================
    # Application-Specific Tests
    # ========================================================================
    
    def test_register_application_build(self):
        """Test application build registration."""
        # Register application task
        task_data = {
            'name': 'build_test_app',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        
        task_id = self.registry.register_task_submission(
            task_data=task_data,
            workspace_dir='/tmp/build_test'
        )
        
        # Register build completion
        build_data = {
            'binary_path': '/tmp/build_test/bin/app',
            'build_artifacts': ['app', 'lib.so', 'config.conf'],
            'module_file_path': '/tmp/build_test/modules/app.lua',
            'build_config': {
                'compiler': 'gcc',
                'version': '11.2',
                'flags': ['-O2', '-march=native']
            },
            'build_success': True,
            'build_duration_seconds': 120,
            'build_log_summary': 'Build completed successfully'
        }
        
        success = self.registry.register_application_build(task_id, build_data)
        self.assertTrue(success)
        
        # Verify application data
        binary_path = self.registry.get_application_binary(task_id)
        self.assertEqual(binary_path, '/tmp/build_test/bin/app')
        
        # Verify task status updated
        task = self.registry.db.get_task(task_id)
        self.assertEqual(task['status'], 'COMPLETED')
        
        # Verify application details
        query = "SELECT * FROM applications WHERE task_id = ?"
        results = self.registry.db.execute_query(query, (task_id,))
        app = results[0]
        
        self.assertTrue(app['build_success'])
        self.assertEqual(app['build_duration_seconds'], 120)
        
        artifacts = json.loads(app['build_artifacts'])
        self.assertEqual(len(artifacts), 3)
        self.assertIn('app', artifacts)
    
    def test_get_application_binary_missing(self):
        """Test getting binary for non-existent application."""
        binary_path = self.registry.get_application_binary('nonexistent_id')
        self.assertIsNone(binary_path)
    
    # ========================================================================
    # Benchmark-Specific Tests  
    # ========================================================================
    
    def test_register_benchmark_results(self):
        """Test benchmark results registration."""
        # Register benchmark task
        task_data = {
            'name': 'results_test_benchmark',
            'version': '1.0',
            'task_type': 'benchmark',
            'config': {}
        }
        
        task_id = self.registry.register_task_submission(
            task_data=task_data,
            workspace_dir='/tmp/results_test'
        )
        
        # Register results
        results_data = {
            'performance_metrics': {
                'runtime': 45.2,
                'memory_usage': 1024,
                'cpu_utilization': 87.5
            },
            'output_files': ['results.txt', 'performance.csv'],
            'extraction_method': 'automatic',
            'validated': True
        }
        
        figures_of_merit = {
            'throughput': 1000.5,
            'latency': 0.045,
            'efficiency': 92.3
        }
        
        success = self.registry.register_benchmark_results(
            task_id, results_data, figures_of_merit
        )
        self.assertTrue(success)
        
        # Verify results retrieval
        retrieved_results = self.registry.get_benchmark_results(task_id)
        self.assertIsNotNone(retrieved_results)
        
        self.assertEqual(retrieved_results['figures_of_merit']['throughput'], 1000.5)
        self.assertEqual(retrieved_results['figures_of_merit']['latency'], 0.045)
        self.assertTrue(retrieved_results['validated'])
        self.assertEqual(len(retrieved_results['output_files']), 2)
        
        # Verify task status updated
        task = self.registry.db.get_task(task_id)
        self.assertEqual(task['status'], 'COMPLETED')
    
    def test_get_benchmark_results_missing(self):
        """Test getting results for non-existent benchmark."""
        results = self.registry.get_benchmark_results('nonexistent_id')
        self.assertIsNone(results)
    
    # ========================================================================
    # Dependency Management Tests
    # ========================================================================
    
    def test_add_task_dependency(self):
        """Test adding task dependencies."""
        # Create dependency task (application)
        app_task_data = {
            'name': 'dependency_app',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        dep_task_id = self.registry.register_task_submission(
            app_task_data, '/tmp/dep_app'
        )
        
        # Create dependent task (benchmark)
        bench_task_data = {
            'name': 'dependent_benchmark',
            'version': '1.0',
            'task_type': 'benchmark',
            'config': {}
        }
        dependent_task_id = self.registry.register_task_submission(
            bench_task_data, '/tmp/dep_bench'
        )
        
        # Add dependency
        dependency_config = {
            'binary_name': 'app_binary',
            'module_required': True,
            'optional': False
        }
        
        success = self.registry.add_task_dependency(
            dependent_task_id, dep_task_id, 'runtime', dependency_config
        )
        self.assertTrue(success)
        
        # Verify dependency resolution
        dependencies = self.registry.resolve_dependencies(dependent_task_id)
        self.assertEqual(len(dependencies), 1)
        
        dep = dependencies[0]
        self.assertEqual(dep['task_id'], dep_task_id)
        self.assertEqual(dep['role'], 'runtime')
        self.assertEqual(dep['name'], 'dependency_app')
        self.assertEqual(dep['task_type'], 'application')
        self.assertFalse(dep['optional'])
        self.assertEqual(dep['config']['binary_name'], 'app_binary')
    
    def test_resolve_dependencies_empty(self):
        """Test dependency resolution for task with no dependencies."""
        task_data = {
            'name': 'no_deps_task',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        task_id = self.registry.register_task_submission(task_data, '/tmp/no_deps')
        
        dependencies = self.registry.resolve_dependencies(task_id)
        self.assertEqual(len(dependencies), 0)
    
    # ========================================================================
    # Status and Query Tests
    # ========================================================================
    
    def test_get_task_status(self):
        """Test task status retrieval."""
        task_data = {
            'name': 'status_test',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        task_id = self.registry.register_task_submission(task_data, '/tmp/status_test')
        
        # Initial status
        status = self.registry.get_task_status(task_id)
        self.assertEqual(status, 'SUBMITTED')
        
        # Update status
        self.registry.update_task_completion(task_id, {'status': 'COMPLETED'})
        status = self.registry.get_task_status(task_id)
        self.assertEqual(status, 'COMPLETED')
        
        # Non-existent task
        status = self.registry.get_task_status('nonexistent')
        self.assertEqual(status, 'NOT_FOUND')
    
    def test_find_tasks(self):
        """Test task search functionality."""
        # Create multiple test tasks
        tasks = [
            {'name': 'find_test_1', 'version': '1.0', 'task_type': 'application'},
            {'name': 'find_test_2', 'version': '1.0', 'task_type': 'benchmark'},
            {'name': 'find_test_1', 'version': '2.0', 'task_type': 'application'},
            {'name': 'other_test', 'version': '1.0', 'task_type': 'application'}
        ]
        
        task_ids = []
        for i, task_data in enumerate(tasks):
            task_data['config'] = {}
            task_id = self.registry.register_task_submission(
                task_data, f'/tmp/find_test_{i}'
            )
            task_ids.append(task_id)
        
        # Test search by name
        results = self.registry.find_tasks({'name': 'find_test_1'})
        self.assertEqual(len(results), 2)
        
        # Test search by task_type
        results = self.registry.find_tasks({'task_type': 'benchmark'})
        self.assertEqual(len(results), 1)
        
        # Test search with status filter
        results = self.registry.find_tasks(
            {'name': 'find_test_1'}, 
            include_states=['SUBMITTED']
        )
        self.assertEqual(len(results), 2)
    
    def test_list_applications(self):
        """Test application listing."""
        # Create mixed tasks
        app_data = {
            'name': 'list_app',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        app_id = self.registry.register_task_submission(app_data, '/tmp/list_app')
        
        bench_data = {
            'name': 'list_bench',
            'version': '1.0',
            'task_type': 'benchmark',
            'config': {}
        }
        bench_id = self.registry.register_task_submission(bench_data, '/tmp/list_bench')
        
        # List applications
        apps = self.registry.list_applications(status_filter="SUBMITTED")
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]['name'], 'list_app')
        self.assertEqual(apps[0]['task_type'], 'application')
    
    def test_list_benchmarks(self):
        """Test benchmark listing with result filtering."""
        # Create benchmarks with and without results
        bench_with_results_data = {
            'name': 'bench_with_results',
            'version': '1.0',
            'task_type': 'benchmark',
            'config': {}
        }
        bench_with_id = self.registry.register_task_submission(
            bench_with_results_data, '/tmp/bench_with'
        )
        
        bench_without_results_data = {
            'name': 'bench_without_results',
            'version': '1.0',
            'task_type': 'benchmark',
            'config': {}
        }
        bench_without_id = self.registry.register_task_submission(
            bench_without_results_data, '/tmp/bench_without'
        )
        
        # Add results to one benchmark
        self.registry.register_benchmark_results(
            bench_with_id, {'test': 'data'}, {'score': 100}
        )
        
        # Test listing all benchmarks
        all_benchmarks = self.registry.list_benchmarks()
        self.assertEqual(len(all_benchmarks), 2)
        
        # Test listing benchmarks with results
        with_results = self.registry.list_benchmarks(has_results=True)
        self.assertEqual(len(with_results), 1)
        self.assertEqual(with_results[0]['name'], 'bench_with_results')
        
        # Test listing benchmarks without results
        without_results = self.registry.list_benchmarks(has_results=False)
        self.assertEqual(len(without_results), 1)
        self.assertEqual(without_results[0]['name'], 'bench_without_results')
    
    # ========================================================================
    # Reproducibility Tests
    # ========================================================================
    
    def test_rerun_task(self):
        """Test task rerun functionality."""
        # Create original task
        original_task_data = {
            'name': 'rerun_test',
            'version': '1.0',
            'task_type': 'benchmark',
            'config': {
                'input_size': 1000,
                'iterations': 10
            }
        }
        
        original_task_id = self.registry.register_task_submission(
            original_task_data, '/tmp/original'
        )
        
        # Complete original task
        self.registry.update_task_completion(original_task_id, {'status': 'COMPLETED'})
        
        # Configure mock workspace manager for rerun
        self.mock_workspace_manager.create_workspace.return_value = '/tmp/rerun_workspace'
        
        # Create rerun with overrides
        config_overrides = {
            'input_size': 2000,
            'iterations': 20
        }
        
        new_task_id = self.registry.rerun_task(
            original_task_id, 
            config_overrides, 
            "Performance comparison study"
        )
        
        self.assertIsNotNone(new_task_id)
        self.assertNotEqual(new_task_id, original_task_id)
        
        # Verify new task configuration
        new_task = self.registry.db.get_task(new_task_id)
        self.assertEqual(new_task['name'], 'rerun_test')
        self.assertEqual(new_task['config_snapshot']['input_size'], 2000)
        self.assertEqual(new_task['config_snapshot']['iterations'], 20)
        
        # Verify rerun history recorded
        query = """
            SELECT * FROM rerun_history 
            WHERE original_task_id = ? AND new_task_id = ?
        """
        results = self.registry.db.execute_query(query, (original_task_id, new_task_id))
        self.assertEqual(len(results), 1)
        
        rerun_record = results[0]
        self.assertEqual(rerun_record['rerun_reason'], "Performance comparison study")
        
        config_diff = json.loads(rerun_record['config_differences'])
        self.assertEqual(config_diff['input_size'], 2000)
    
    def test_recreate_task_config(self):
        """Test task configuration recreation."""
        task_data = {
            'name': 'config_recreation_test',
            'version': '1.0',
            'task_type': 'application',
            'config': {
                'compiler': 'gcc',
                'flags': ['-O3', '-march=native'],
                'modules': ['gcc/11.2', 'openmpi/4.1']
            },
            'cli_overrides': {'parallel': True}
        }
        
        task_id = self.registry.register_task_submission(task_data, '/tmp/config_test')
        
        # Recreate configuration
        recreated_config = self.registry.recreate_task_config(task_id)
        
        self.assertEqual(recreated_config['name'], 'config_recreation_test')
        self.assertEqual(recreated_config['config']['compiler'], 'gcc')
        self.assertEqual(len(recreated_config['config']['flags']), 2)
        self.assertTrue(recreated_config['cli_overrides']['parallel'])
    
    # ========================================================================
    # Historical Analysis Tests
    # ========================================================================
    
    
    
    # ========================================================================
    # Maintenance and Validation Tests
    # ========================================================================
    
    
    def test_mark_workspace_cleaned(self):
        """Test marking workspace as cleaned."""
        task_data = {
            'name': 'cleaned_workspace_test',
            'version': '1.0',
            'task_type': 'application',
            'config': {}
        }
        task_id = self.registry.register_task_submission(task_data, '/tmp/cleaned_test')
        
        # Mark as cleaned
        success = self.registry.mark_workspace_cleaned(task_id)
        self.assertTrue(success)
        
        # Verify in database
        task = self.registry.db.get_task(task_id)
        self.assertTrue(task['files_cleaned'])
    
    # ========================================================================
    # Error Handling Tests
    # ========================================================================
    
    def test_register_build_nonexistent_task(self):
        """Test registering build for non-existent task."""
        build_data = {
            'binary_path': '/tmp/test/bin/app',
            'build_success': True
        }
        
        success = self.registry.register_application_build('nonexistent_id', build_data)
        self.assertFalse(success)
    
    def test_rerun_nonexistent_task(self):
        """Test rerunning non-existent task."""
        with self.assertRaises(ValueError) as context:
            self.registry.rerun_task('nonexistent_id')
        
        self.assertIn('Original task not found', str(context.exception))
    
    def test_recreate_config_nonexistent_task(self):
        """Test recreating config for non-existent task."""
        with self.assertRaises(ValueError) as context:
            self.registry.recreate_task_config('nonexistent_id')
        
        self.assertIn('Task not found', str(context.exception))


if __name__ == '__main__':
    unittest.main() 