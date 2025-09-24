# BenchPRO Database Setup

This directory contains scripts for setting up and managing the BenchPRO database.

## Prerequisites

- Python 3.8+ (tested with Python 3.13.3)
- SQLite3 (built into Python, external CLI optional)

## Initial Database Setup

### Quick Start

To set up the database with default settings:

```bash
python3 scripts/setup_database.py
```

This creates the database at `~/.benchpro/registry/benchpro.db` with the complete schema.

### Custom Database Location

```bash
python3 scripts/setup_database.py --db-path /path/to/your/database.db
```

### Force Recreate Database

```bash
python3 scripts/setup_database.py --force
```

### Verbose Output

```bash
python3 scripts/setup_database.py --verbose
```

## Database Schema

The setup script creates a comprehensive database schema with the following tables:

- **`tasks`** - Main tasks table (unified for applications and benchmarks)
- **`applications`** - Application-specific data (build artifacts, binaries)
- **`benchmarks`** - Benchmark-specific data (execution config, results)
- **`benchmark_results`** - Results storage with figures of merit
- **`task_dependencies`** - Flexible dependency relationships
- **`system_environments`** - System snapshots for reproducibility
- **`rerun_history`** - Rerun tracking for analysis
- **`workspace_fingerprints`** - Workspace metadata for future ingest
- **`database_metadata`** - Schema versioning and metadata

## Portability

### New System Setup

1. **Copy the script**:
   ```bash
   curl -O https://your-repo/scripts/setup_database.py
   # or copy the file manually
   ```

2. **Run setup**:
   ```bash
   python3 setup_database.py
   ```

3. **Verify installation**:
   ```bash
   sqlite3 ~/.benchpro/registry/benchpro.db ".tables"
   ```

### System Requirements

- **macOS**: SQLite is pre-installed
- **Linux**: Usually pre-installed, or install with package manager:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install sqlite3
  
  # CentOS/RHEL
  sudo yum install sqlite
  ```
- **Windows**: SQLite is included with Python

### Docker/Container Setup

```dockerfile
FROM python:3.11
COPY setup_database.py /app/
RUN python3 /app/setup_database.py --db-path /data/benchpro.db
```

## Database Verification

After setup, verify the database:

```bash
# Check tables exist
sqlite3 ~/.benchpro/registry/benchpro.db ".tables"

# Check schema version
sqlite3 ~/.benchpro/registry/benchpro.db "SELECT value FROM database_metadata WHERE key='schema_version';"

# Check integrity
sqlite3 ~/.benchpro/registry/benchpro.db "PRAGMA integrity_check;"
```

## Migration and Upgrades

For future schema changes, the script includes:

- **Schema versioning** in `database_metadata` table
- **Non-destructive updates** with `IF NOT EXISTS` clauses
- **Force recreation** option for major changes

## Troubleshooting

### Permission Denied
```bash
mkdir -p ~/.benchpro/registry
chmod 755 ~/.benchpro/registry
```

### Database Locked
```bash
# Check for active connections
lsof ~/.benchpro/registry/benchpro.db

# Force recreate if needed
python3 scripts/setup_database.py --force
```

### Corrupted Database
```bash
# Check integrity
sqlite3 ~/.benchpro/registry/benchpro.db "PRAGMA integrity_check;"

# Recreate if corrupted
python3 scripts/setup_database.py --force
```

## Development

### Adding New Tables

1. Update `DATABASE_SCHEMA` in `setup_database.py`
2. Add indexes to `DATABASE_INDEXES` if needed
3. Increment schema version in `DATABASE_METADATA`
4. Test with `--force` option

### Testing Schema Changes

```bash
# Test in temporary location
python3 scripts/setup_database.py --db-path /tmp/test.db --verbose

# Verify schema
sqlite3 /tmp/test.db ".schema"
``` 