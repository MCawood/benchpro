#!/usr/bin/env python3
"""
BenchPRO Database Setup Script

This script creates and initializes the BenchPRO database with the complete schema
for the new registry system. It can be run on any system to set up the database
for the first time.

Usage:
    python setup_database.py [--db-path /path/to/database.db] [--force]
    
Options:
    --db-path: Custom database path (default: ~/.benchpro/registry/benchpro.db)
    --force: Recreate database even if it exists
"""

import sqlite3
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Database schema from REGISTRY_REWORK_PLAN.md
DATABASE_SCHEMA = """
-- Main tasks table (unified for both applications and benchmarks)
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN ('application', 'benchmark')),
    submission_time DATETIME NOT NULL,
    completion_time DATETIME,
    status TEXT NOT NULL,
    
    -- Workspace information
    workspace_dir TEXT,                     -- Current workspace location  
    workspace_pattern TEXT,                -- Pattern for recreation
    files_cleaned BOOLEAN DEFAULT FALSE,   -- Whether workspace was cleaned
    
    -- Reproducibility data
    config_snapshot TEXT NOT NULL,         -- Complete config JSON at execution
    system_snapshot_id TEXT,               -- Reference to system environment
    template_content TEXT,                 -- Template used for generation
    cli_overrides TEXT,                    -- JSON of CLI parameter overrides
    
    -- Metadata and tracking
    description TEXT,
    tags TEXT,                             -- JSON array of tags
    ingest_source TEXT DEFAULT 'benchpro_generated', -- 'benchpro_generated' or 'manual_ingest'
    workspace_hash TEXT,                   -- Hash of workspace contents
    metadata_version TEXT DEFAULT '1.0',   -- Version of metadata format
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (system_snapshot_id) REFERENCES system_environments(id)
);

-- Application-specific data (things that are built)
CREATE TABLE IF NOT EXISTS applications (
    task_id TEXT PRIMARY KEY,
    
    -- Build outputs
    binary_path TEXT,                       -- Primary binary location
    build_artifacts TEXT,                   -- JSON list of all build outputs
    module_file_path TEXT,                  -- Generated module file
    
    -- Build metadata
    build_config TEXT,                      -- Build-specific configuration
    build_success BOOLEAN DEFAULT FALSE,
    build_duration_seconds INTEGER,
    build_log_summary TEXT,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Benchmark-specific data (things that are executed for results)
CREATE TABLE IF NOT EXISTS benchmarks (
    task_id TEXT PRIMARY KEY,
    
    -- Execution configuration
    execution_config TEXT,                  -- Execution-specific config
    input_specification TEXT,               -- Input data/parameters
    has_application_dependencies BOOLEAN DEFAULT FALSE,
    
    -- Execution metadata
    execution_duration_seconds INTEGER,
    execution_log_summary TEXT,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Results storage (only for benchmarks)
CREATE TABLE IF NOT EXISTS benchmark_results (
    benchmark_id TEXT PRIMARY KEY,
    
    -- Results data
    results_data TEXT,                      -- JSON of all extracted results
    figures_of_merit TEXT,                  -- JSON of key metrics {metric: value}
    performance_metrics TEXT,               -- JSON of performance data
    
    -- Result files and extraction
    output_files_captured TEXT,             -- JSON list of captured files
    result_extraction_method TEXT,          -- How results were extracted
    
    -- Validation and metadata
    results_validated BOOLEAN DEFAULT FALSE,
    validation_notes TEXT,
    extracted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(task_id)
);

-- Flexible dependency system supporting modular applications
CREATE TABLE IF NOT EXISTS task_dependencies (
    dependent_task_id TEXT NOT NULL,       -- Task that depends
    dependency_task_id TEXT NOT NULL,      -- Task that is depended upon
    
    -- Dependency metadata
    dependency_role TEXT NOT NULL,         -- 'build', 'runtime', 'data', 'module'
    dependency_name TEXT,                  -- Named role (e.g., 'mpi_library')
    optional BOOLEAN DEFAULT FALSE,        -- Whether dependency is optional
    
    -- Usage configuration
    dependency_config TEXT,                -- JSON: how dependency is used
    binary_path_used TEXT,                 -- Specific binary path used
    module_loaded TEXT,                    -- Module that was loaded
    
    -- Ordering and constraints
    execution_order INTEGER,               -- Order if multiple dependencies
    version_constraint TEXT,               -- Version requirements
    
    PRIMARY KEY (dependent_task_id, dependency_task_id, dependency_role),
    FOREIGN KEY (dependent_task_id) REFERENCES tasks(id),
    FOREIGN KEY (dependency_task_id) REFERENCES tasks(id)
);

-- System environment snapshots for reproducibility
CREATE TABLE IF NOT EXISTS system_environments (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    
    -- Module system state
    modules_available TEXT,                 -- JSON of available modules
    module_paths TEXT,                      -- JSON of module paths
    
    -- System information
    os_info TEXT,                          -- JSON of OS information
    hardware_info TEXT,                    -- JSON of hardware specs
    compiler_info TEXT,                    -- JSON of available compilers
    environment_vars TEXT,                 -- JSON of relevant env vars
    
    captured_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Rerun tracking for reproducibility analysis
CREATE TABLE IF NOT EXISTS rerun_history (
    id TEXT PRIMARY KEY,
    original_task_id TEXT NOT NULL,
    new_task_id TEXT NOT NULL,
    
    rerun_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    rerun_reason TEXT,                      -- Why was this rerun?
    config_differences TEXT,               -- JSON of any config changes
    result_comparison TEXT,                -- JSON comparison of results
    reproducibility_verified BOOLEAN,
    
    FOREIGN KEY (original_task_id) REFERENCES tasks(id),
    FOREIGN KEY (new_task_id) REFERENCES tasks(id)
);

-- Workspace fingerprints for future ingest capability
CREATE TABLE IF NOT EXISTS workspace_fingerprints (
    task_id TEXT PRIMARY KEY,
    directory_structure TEXT,              -- JSON of directory tree
    file_hashes TEXT,                      -- JSON of critical file hashes
    metadata_files TEXT,                   -- JSON of metadata file contents
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
"""

# Performance indexes from the plan
DATABASE_INDEXES = """
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_tasks_name_version ON tasks(name, version);
CREATE INDEX IF NOT EXISTS idx_tasks_task_type ON tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_tasks_submission_time ON tasks(submission_time);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_dependencies_dependent ON task_dependencies(dependent_task_id);
CREATE INDEX IF NOT EXISTS idx_dependencies_dependency ON task_dependencies(dependency_task_id);
CREATE INDEX IF NOT EXISTS idx_benchmarks_has_deps ON benchmarks(has_application_dependencies);
"""

# Initial metadata for database versioning
DATABASE_METADATA = """
-- Database metadata table for schema versioning
CREATE TABLE IF NOT EXISTS database_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial metadata
INSERT OR REPLACE INTO database_metadata (key, value) VALUES 
    ('schema_version', '1.0'),
    ('created_by', 'setup_database.py'),
    ('benchpro_version', '2.0'),
    ('created_at', datetime('now'));
"""


def get_default_db_path() -> str:
    """Get the default database path in user directory."""
    home = Path.home()
    db_dir = home / '.benchpro' / 'registry'
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / 'benchpro.db')


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_database_exists(db_path: str) -> bool:
    """Check if database file exists and has tables."""
    if not os.path.exists(db_path):
        return False
        
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks';")
            return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def create_database(db_path: str, force: bool = False) -> bool:
    """
    Create and initialize the BenchPRO database.
    
    Args:
        db_path: Path to the database file
        force: If True, recreate database even if it exists
        
    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Check if database exists
    if check_database_exists(db_path) and not force:
        logger.info(f"Database already exists at {db_path}")
        logger.info("Use --force to recreate the database")
        return True
    
    # Create database directory if needed
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")
    
    try:
        # Connect to database (creates file if it doesn't exist)
        logger.info(f"{'Recreating' if force else 'Creating'} database at: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # If force, drop existing tables
            if force:
                logger.info("Dropping existing tables...")
                # Get all table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table[0]};")
                conn.commit()
            
            # Create tables
            logger.info("Creating database schema...")
            cursor.executescript(DATABASE_SCHEMA)
            conn.commit()
            
            # Create indexes
            logger.info("Creating performance indexes...")
            cursor.executescript(DATABASE_INDEXES)
            conn.commit()
            
            # Insert metadata
            logger.info("Inserting database metadata...")
            cursor.executescript(DATABASE_METADATA)
            conn.commit()
            
            # Verify database integrity
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()
            if integrity_result[0] != "ok":
                raise sqlite3.Error(f"Database integrity check failed: {integrity_result[0]}")
            
        logger.info("Database created successfully!")
        logger.info(f"Database location: {os.path.abspath(db_path)}")
        
        # Display database info
        display_database_info(db_path)
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def display_database_info(db_path: str) -> None:
    """Display information about the created database."""
    logger = logging.getLogger(__name__)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get table count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
            table_count = cursor.fetchone()[0]
            
            # Get index count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index';")
            index_count = cursor.fetchone()[0]
            
            # Get database size
            db_size = os.path.getsize(db_path)
            
            logger.info("Database Information:")
            logger.info(f"  Tables created: {table_count}")
            logger.info(f"  Indexes created: {index_count}")
            logger.info(f"  Database size: {db_size} bytes")
            logger.info(f"  SQLite version: {sqlite3.sqlite_version}")
            
            # List tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"  Tables: {', '.join(tables)}")
            
    except sqlite3.Error as e:
        logger.error(f"Error displaying database info: {e}")


def main():
    """Main entry point for the database setup script."""
    parser = argparse.ArgumentParser(
        description="Initialize BenchPRO database with complete schema",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help=f"Database path (default: {get_default_db_path()})"
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help="Recreate database even if it exists"
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Determine database path
    db_path = args.db_path or get_default_db_path()
    
    logger.info("BenchPRO Database Setup")
    logger.info("=" * 40)
    
    # Create database
    success = create_database(db_path, args.force)
    
    if success:
        logger.info("Database setup completed successfully!")
        return 0
    else:
        logger.error("Database setup failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 