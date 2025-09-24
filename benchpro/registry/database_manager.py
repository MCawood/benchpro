"""
Database Manager for BenchPRO Registry.

This module provides low-level database operations, connection management,
and utilities for the new database-backed registry system.
"""

import sqlite3
import json
import threading
import logging
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

from benchpro.utils.user_dir import get_user_dir_manager
from benchpro.utils.logger import get_logger


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class DatabaseManager:
    """
    Low-level database operations manager for BenchPRO registry.
    
    Responsibilities:
    - Database connection management with pooling
    - Transaction handling
    - Schema validation and integrity checks
    - Basic CRUD operations with type conversion
    - JSON serialization/deserialization
    - Concurrent access handling
    """
    
    def __init__(self, db_path: Optional[str] = None, 
                 user_dir_manager=None):
        """
        Initialize the DatabaseManager.
        
        Args:
            db_path: Path to the database file. If None, uses default path.
            user_dir_manager: UserDirectoryManager instance.
        """
        # Setup logging
        self.logger = get_logger(__name__)
        
        # User directory manager
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
        # Determine database path
        if db_path is None:
            db_path = self.user_dir_manager.get_path("registry", "benchpro.db")
        self.db_path = db_path
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Connection settings
        self._connection_timeout = 30.0
        self._transaction_timeout = 10.0
        
        self.logger.debug(f"DatabaseManager initialized with path: {self.db_path}")
        
        # Ensure database exists and is valid
        self._ensure_database_exists()
    
    def _ensure_database_exists(self) -> None:
        """Ensure database exists and has proper schema."""
        if not os.path.exists(self.db_path):
            self.logger.warning(f"Database not found at {self.db_path}")
            self.logger.info("Run 'python scripts/setup_database.py' to create the database")
            raise DatabaseError(f"Database not found at {self.db_path}. Run setup script first.")
        
        # Verify basic schema
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks';")
                if not cursor.fetchone():
                    raise DatabaseError("Database schema is invalid - tasks table not found")
                    
                # Check schema version
                try:
                    cursor.execute("SELECT value FROM database_metadata WHERE key='schema_version';")
                    version = cursor.fetchone()
                    if version:
                        self.logger.debug(f"Database schema version: {version[0]}")
                    else:
                        self.logger.warning("Schema version not found in database")
                except sqlite3.OperationalError:
                    self.logger.warning("Database metadata table not found")
                    
        except sqlite3.Error as e:
            raise DatabaseError(f"Database validation failed: {e}")
    
    @contextmanager
    def get_connection(self):
        """
        Get a database connection with proper setup.
        
        Uses thread-local storage to ensure connection safety.
        """
        # Get thread-local connection
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                self._local.connection = sqlite3.connect(
                    self.db_path,
                    timeout=self._connection_timeout,
                    check_same_thread=False
                )
                
                # Configure connection
                self._local.connection.execute("PRAGMA foreign_keys = ON;")
                self._local.connection.execute("PRAGMA journal_mode = WAL;")  # Better concurrency
                self._local.connection.execute("PRAGMA synchronous = NORMAL;")  # Performance vs safety
                
                # Row factory for named access
                self._local.connection.row_factory = sqlite3.Row
                
            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to connect to database: {e}")
        
        try:
            yield self._local.connection
        except sqlite3.Error as e:
            # Rollback on error
            if self._local.connection:
                self._local.connection.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Automatically commits on success, rolls back on error.
        """
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION;")
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise DatabaseError(f"Transaction failed: {e}")
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of query results as Row objects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: Tuple = ()) -> str:
        """
        Execute an INSERT query and return the last inserted row ID.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Last inserted row ID as string
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return str(cursor.lastrowid)
    
    def insert_task(self, task_data: Dict[str, Any]) -> str:
        """
        Insert a new task into the database.
        
        Args:
            task_data: Task data dictionary
            
        Returns:
            Task ID
        """
        # Generate task ID if not provided
        task_id = task_data.get('id', self._generate_task_id(
            task_data['name'], 
            task_data.get('version', '1.0')
        ))
        
        # Prepare data with JSON serialization
        insert_data = {
            'id': task_id,
            'name': task_data['name'],
            'version': str(task_data.get('version', '1.0')),
            'task_type': task_data['task_type'],
            'submission_time': task_data.get('submission_time', self._current_timestamp()),
            'completion_time': task_data.get('completion_time'),
            'status': task_data.get('status', 'SUBMITTED'),
            'workspace_dir': task_data.get('workspace_dir'),
            'workspace_pattern': task_data.get('workspace_pattern'),
            'files_cleaned': task_data.get('files_cleaned', False),
            'config_snapshot': self._serialize_json(task_data.get('config_snapshot', {})),
            'system_snapshot_id': task_data.get('system_snapshot_id'),
            'template_content': task_data.get('template_content'),
            'cli_overrides': self._serialize_json(task_data.get('cli_overrides', {})),
            'description': task_data.get('description'),
            'tags': self._serialize_json(task_data.get('tags', [])),
            'ingest_source': task_data.get('ingest_source', 'benchpro_generated'),
            'workspace_hash': task_data.get('workspace_hash'),
            'metadata_version': task_data.get('metadata_version', '1.0')
        }
        
        # Insert query
        columns = ', '.join(insert_data.keys())
        placeholders = ', '.join(['?' for _ in insert_data])
        query = f"INSERT INTO tasks ({columns}) VALUES ({placeholders})"
        
        try:
            self.execute_update(query, tuple(insert_data.values()))
            self.logger.debug(f"Inserted task: {task_id}")
            return task_id
        except DatabaseError as e:
            self.logger.error(f"Failed to insert task {task_id}: {e}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task data dictionary or None if not found
        """
        query = "SELECT * FROM tasks WHERE id = ?"
        results = self.execute_query(query, (task_id,))
        
        if results:
            return self._row_to_dict(results[0])
        return None
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update task data.
        
        Args:
            task_id: Task ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False if task not found
        """
        # Prepare updates with JSON serialization
        update_fields = []
        update_values = []
        
        for key, value in updates.items():
            if key in ['config_snapshot', 'cli_overrides', 'tags']:
                value = self._serialize_json(value)
            elif key == 'version':
                value = str(value)
            
            update_fields.append(f"{key} = ?")
            update_values.append(value)
        
        # Add updated_at timestamp
        update_fields.append("updated_at = ?")
        update_values.append(self._current_timestamp())
        
        # Add task_id for WHERE clause
        update_values.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
        
        try:
            rows_affected = self.execute_update(query, tuple(update_values))
            success = rows_affected > 0
            if success:
                self.logger.debug(f"Updated task: {task_id}")
            else:
                self.logger.warning(f"Task not found for update: {task_id}")
            return success
        except DatabaseError as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
            raise
    
    def find_tasks(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find tasks matching criteria.
        
        Args:
            criteria: Search criteria dictionary
            
        Returns:
            List of matching tasks
        """
        where_clauses = []
        params = []
        
        # Build WHERE clauses
        for key, value in criteria.items():
            if key in ['name', 'version', 'task_type', 'status', 'job_id']:
                where_clauses.append(f"{key} = ?")
                params.append(str(value))
            elif key == 'since':
                where_clauses.append("submission_time >= ?")
                params.append(value)
            elif key == 'until':
                where_clauses.append("submission_time <= ?")
                params.append(value)
            elif key == 'tags':
                # JSON search for tags (simplified)
                where_clauses.append("tags LIKE ?")
                params.append(f'%"{value}"%')
        
        # Build query
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT * FROM tasks WHERE {where_clause} ORDER BY submission_time DESC"
        
        results = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in results]
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert a database row to a dictionary with JSON deserialization.
        """
        data = dict(row)
        
        # Deserialize JSON fields
        json_fields = ['config_snapshot', 'cli_overrides', 'tags']
        for field in json_fields:
            if data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    data[field] = {}
        
        return data
    
    def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string."""
        if data is None:
            return ""
        try:
            return json.dumps(data, default=str)
        except (TypeError, ValueError):
            return json.dumps(str(data))
    
    def _current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def _generate_task_id(self, name: str, version: str) -> str:
        """
        Generate a unique task ID.
        
        Args:
            name: Task name
            version: Task version
            
        Returns:
            Unique task ID string
        """
        import random
        import string
        
        # Clean version for ID
        version_clean = str(version).replace(".", "")
        
        # Generate random suffix
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Unix timestamp for uniqueness
        timestamp = int(time.time())
        
        return f"{name}_{version_clean}_{timestamp}_{suffix}"
    
    def check_integrity(self) -> Tuple[bool, List[str]]:
        """
        Check database integrity.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # SQLite integrity check
                cursor.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()
                if result[0] != "ok":
                    issues.append(f"SQLite integrity check failed: {result[0]}")
                
                # Foreign key check
                cursor.execute("PRAGMA foreign_key_check;")
                fk_violations = cursor.fetchall()
                if fk_violations:
                    issues.extend([f"Foreign key violation: {row}" for row in fk_violations])
                
                # Check for orphaned application/benchmark entries
                cursor.execute("""
                    SELECT COUNT(*) FROM applications 
                    WHERE task_id NOT IN (SELECT id FROM tasks)
                """)
                orphaned_apps = cursor.fetchone()[0]
                if orphaned_apps > 0:
                    issues.append(f"Found {orphaned_apps} orphaned application entries")
                
                cursor.execute("""
                    SELECT COUNT(*) FROM benchmarks 
                    WHERE task_id NOT IN (SELECT id FROM tasks)
                """)
                orphaned_benchmarks = cursor.fetchone()[0]
                if orphaned_benchmarks > 0:
                    issues.append(f"Found {orphaned_benchmarks} orphaned benchmark entries")
        
        except Exception as e:
            issues.append(f"Integrity check failed: {e}")
        
        return len(issues) == 0, issues
    
    def cleanup_connections(self) -> None:
        """Clean up database connections."""
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
                self._local.connection = None
                self.logger.debug("Database connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup_connections() 