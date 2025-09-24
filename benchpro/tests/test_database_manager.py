"""
Unit tests for DatabaseManager.

Tests the low-level database operations, connection management,
and integrity checking functionality.
"""

import os
import tempfile
import unittest
import sqlite3
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from benchpro.registry.database_manager import DatabaseManager, DatabaseError


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_benchpro.db")
        
        # Create test database with schema
        self._create_test_database()
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.test_db_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up database connections
        if hasattr(self, 'db_manager'):
            self.db_manager.cleanup_connections()
        
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_database(self):
        """Create test database with proper schema."""
        # Use the setup script to create database
        import subprocess
        result = subprocess.run([
            'python3', 'scripts/setup_database.py', 
            '--db-path', self.test_db_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Fallback: create minimal schema manually
            conn = sqlite3.connect(self.test_db_path)
            conn.execute("PRAGMA foreign_keys = ON;")
            
            # Create minimal tables for testing
            conn.executescript("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    task_type TEXT NOT NULL,
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
                
                CREATE TABLE database_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                INSERT INTO database_metadata (key, value) VALUES 
                    ('schema_version', '1.0'),
                    ('created_by', 'test_setup');
            """)
            conn.commit()
            conn.close()
    
    def test_initialization(self):
        """Test database manager initialization."""
        self.assertIsNotNone(self.db_manager)
        self.assertEqual(self.db_manager.db_path, self.test_db_path)
        self.assertTrue(os.path.exists(self.test_db_path))
    
    def test_initialization_missing_database(self):
        """Test initialization with missing database file."""
        missing_db_path = os.path.join(self.temp_dir, "missing.db")
        
        with self.assertRaises(DatabaseError) as context:
            DatabaseManager(missing_db_path)
        
        self.assertIn("Database not found", str(context.exception))
    
    def test_get_connection(self):
        """Test database connection management."""
        with self.db_manager.get_connection() as conn:
            self.assertIsNotNone(conn)
            self.assertIsInstance(conn, sqlite3.Connection)
            
            # Test that foreign keys are enabled
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys;")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)  # Foreign keys enabled
    
    def test_transaction_success(self):
        """Test successful transaction handling."""
        test_data = {
            'name': 'test_app',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {'test': 'data'}
        }
        
        task_id = self.db_manager.insert_task(test_data)
        
        # Verify task was inserted
        task = self.db_manager.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task['name'], 'test_app')
        self.assertEqual(task['task_type'], 'application')
    
    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        with self.assertRaises(DatabaseError):
            with self.db_manager.transaction() as conn:
                cursor = conn.cursor()
                # Insert valid task
                cursor.execute("""
                    INSERT INTO tasks (id, name, version, task_type, submission_time, status, config_snapshot)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ('test_id', 'test', '1.0', 'application', '2024-01-01T00:00:00Z', 'SUBMITTED', '{}'))
                
                # Cause error with invalid foreign key
                cursor.execute("INSERT INTO applications (task_id) VALUES (?)", ('invalid_task_id',))
        
        # Verify rollback - task should not exist
        task = self.db_manager.get_task('test_id')
        self.assertIsNone(task)
    
    def test_insert_task(self):
        """Test task insertion with all fields."""
        task_data = {
            'name': 'comprehensive_test',
            'version': '2.0',
            'task_type': 'benchmark',
            'status': 'SUBMITTED',
            'workspace_dir': '/tmp/test_workspace',
            'config_snapshot': {
                'compiler': 'gcc',
                'flags': '-O2',
                'modules': ['mpi/4.1']
            },
            'cli_overrides': {'threads': 4},
            'description': 'Test benchmark task',
            'tags': ['test', 'benchmark'],
            'workspace_hash': 'abc123'
        }
        
        task_id = self.db_manager.insert_task(task_data)
        
        # Verify insertion
        self.assertIsNotNone(task_id)
        self.assertTrue(task_id.startswith('comprehensive_test_20_'))
        
        # Verify data integrity
        retrieved_task = self.db_manager.get_task(task_id)
        self.assertIsNotNone(retrieved_task)
        self.assertEqual(retrieved_task['name'], 'comprehensive_test')
        self.assertEqual(retrieved_task['version'], '2.0')
        self.assertEqual(retrieved_task['task_type'], 'benchmark')
        
        # Check JSON deserialization
        self.assertIsInstance(retrieved_task['config_snapshot'], dict)
        self.assertEqual(retrieved_task['config_snapshot']['compiler'], 'gcc')
        self.assertEqual(retrieved_task['cli_overrides']['threads'], 4)
        self.assertEqual(len(retrieved_task['tags']), 2)
    
    def test_update_task(self):
        """Test task updates."""
        # Insert initial task
        task_data = {
            'name': 'update_test',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {'initial': 'data'}
        }
        task_id = self.db_manager.insert_task(task_data)
        
        # Update task
        updates = {
            'status': 'COMPLETED',
            'completion_time': '2024-01-01T12:00:00Z',
            'config_snapshot': {'updated': 'data'},
            'tags': ['updated', 'test']
        }
        
        success = self.db_manager.update_task(task_id, updates)
        self.assertTrue(success)
        
        # Verify updates
        updated_task = self.db_manager.get_task(task_id)
        self.assertEqual(updated_task['status'], 'COMPLETED')
        self.assertEqual(updated_task['completion_time'], '2024-01-01T12:00:00Z')
        self.assertEqual(updated_task['config_snapshot']['updated'], 'data')
        self.assertEqual(len(updated_task['tags']), 2)
    
    def test_update_nonexistent_task(self):
        """Test updating non-existent task."""
        success = self.db_manager.update_task('nonexistent_id', {'status': 'COMPLETED'})
        self.assertFalse(success)
    
    def test_find_tasks(self):
        """Test task search functionality."""
        # Insert test tasks
        task_data_1 = {
            'name': 'search_test_1',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {}
        }
        task_data_2 = {
            'name': 'search_test_2',
            'version': '1.0',
            'task_type': 'benchmark',
            'config_snapshot': {}
        }
        task_data_3 = {
            'name': 'search_test_1',
            'version': '2.0',
            'task_type': 'application',
            'config_snapshot': {}
        }
        
        task_id_1 = self.db_manager.insert_task(task_data_1)
        task_id_2 = self.db_manager.insert_task(task_data_2)
        task_id_3 = self.db_manager.insert_task(task_data_3)
        
        # Test search by name
        results = self.db_manager.find_tasks({'name': 'search_test_1'})
        self.assertEqual(len(results), 2)
        task_ids = [task['id'] for task in results]
        self.assertIn(task_id_1, task_ids)
        self.assertIn(task_id_3, task_ids)
        
        # Test search by task_type
        results = self.db_manager.find_tasks({'task_type': 'benchmark'})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], task_id_2)
        
        # Test search with multiple criteria
        results = self.db_manager.find_tasks({
            'name': 'search_test_1',
            'version': '2.0'
        })
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], task_id_3)
    
    def test_json_serialization_edge_cases(self):
        """Test JSON serialization with edge cases."""
        task_data = {
            'name': 'json_test',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {
                'nested': {'deep': {'structure': True}},
                'list': [1, 2, 3],
                'null_value': None,
                'boolean': False,
                'number': 42.5
            },
            'tags': [],  # Empty list
            'cli_overrides': {}  # Empty dict
        }
        
        task_id = self.db_manager.insert_task(task_data)
        retrieved_task = self.db_manager.get_task(task_id)
        
        # Verify complex JSON structure preservation
        config = retrieved_task['config_snapshot']
        self.assertEqual(config['nested']['deep']['structure'], True)
        self.assertEqual(config['list'], [1, 2, 3])
        self.assertIsNone(config['null_value'])
        self.assertEqual(config['boolean'], False)
        self.assertEqual(config['number'], 42.5)
        
        # Verify empty collections
        self.assertEqual(retrieved_task['tags'], [])
        self.assertEqual(retrieved_task['cli_overrides'], {})
    
    def test_task_id_generation(self):
        """Test unique task ID generation."""
        task_data = {
            'name': 'id_test',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {}
        }
        
        # Generate multiple task IDs
        task_ids = []
        for _ in range(5):
            task_id = self.db_manager.insert_task(task_data)
            task_ids.append(task_id)
        
        # Verify uniqueness
        self.assertEqual(len(task_ids), len(set(task_ids)))
        
        # Verify format
        for task_id in task_ids:
            self.assertTrue(task_id.startswith('id_test_10_'))
            parts = task_id.split('_')
            self.assertEqual(len(parts), 5)  # id_test_10_timestamp_suffix (name has underscore)
    
    def test_execute_query(self):
        """Test direct query execution."""
        # Insert test data
        task_data = {
            'name': 'query_test',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {}
        }
        task_id = self.db_manager.insert_task(task_data)
        
        # Test query execution
        results = self.db_manager.execute_query(
            "SELECT name, version FROM tasks WHERE id = ?",
            (task_id,)
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'query_test')
        self.assertEqual(results[0]['version'], '1.0')
    
    def test_execute_update(self):
        """Test direct update execution."""
        # Insert test data
        task_data = {
            'name': 'update_query_test',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {}
        }
        task_id = self.db_manager.insert_task(task_data)
        
        # Test update execution
        rows_affected = self.db_manager.execute_update(
            "UPDATE tasks SET status = ? WHERE id = ?",
            ('COMPLETED', task_id)
        )
        
        self.assertEqual(rows_affected, 1)
        
        # Verify update
        task = self.db_manager.get_task(task_id)
        self.assertEqual(task['status'], 'COMPLETED')
    
    def test_check_integrity(self):
        """Test database integrity checking."""
        is_valid, issues = self.db_manager.check_integrity()
        
        # Should be valid for new database
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
    
    def test_check_integrity_with_orphaned_records(self):
        """Test integrity check with orphaned records."""
        # Insert valid task
        task_data = {
            'name': 'integrity_test',
            'version': '1.0',
            'task_type': 'application',
            'config_snapshot': {}
        }
        task_id = self.db_manager.insert_task(task_data)
        
        # Temporarily disable foreign keys and insert orphaned application record
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF;")
            cursor.execute("INSERT INTO applications (task_id) VALUES (?)", ('orphaned_task_id',))
            conn.commit()
            cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Check integrity
        is_valid, issues = self.db_manager.check_integrity()
        
        self.assertFalse(is_valid)
        self.assertTrue(any('orphaned application' in issue for issue in issues))
    
    def test_connection_cleanup(self):
        """Test connection cleanup."""
        # Create connection
        with self.db_manager.get_connection() as conn:
            self.assertIsNotNone(conn)
        
        # Test cleanup
        self.db_manager.cleanup_connections()
        
        # Should still be able to create new connection
        with self.db_manager.get_connection() as conn:
            self.assertIsNotNone(conn)
    
    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access."""
        import threading
        import time
        
        results = []
        errors = []
        
        def insert_task(thread_id):
            try:
                task_data = {
                    'name': f'concurrent_test_{thread_id}',
                    'version': '1.0',
                    'task_type': 'application',
                    'config_snapshot': {'thread_id': thread_id}
                }
                task_id = self.db_manager.insert_task(task_data)
                results.append(task_id)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=insert_task, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 5)
        self.assertEqual(len(set(results)), 5)  # All unique IDs


if __name__ == '__main__':
    unittest.main() 