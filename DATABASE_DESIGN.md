# Build Registry Database Design

## Context and Requirements

1. We're building a build registry system for HPC applications
2. Each build represents a compiled application (like LAMMPS, OpenFOAM, etc.)
3. Builds are created from YAML templates that specify:
   ```yaml
   name: lammps
   version: "23Jun2022"
   build:
     binary:
       directory: bin
       executable: lmp
   ```
4. We need to track:
   - Build metadata (application, version, status)
   - Build configuration details
   - Installation locations
   - Binary verification (via file hashes)
   - Build dependencies
   - Build process logs

## Proposed Schema

### 1. builds (Main build record table)
```sql
CREATE TABLE builds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,              -- UUID for external reference
    application TEXT NOT NULL,              -- Application name
    version TEXT NOT NULL,                  -- Application version
    status TEXT NOT NULL,                   -- Build status (CREATED, IN_PROGRESS, COMPLETED, FAILED)
    variant TEXT,                           -- Build variant (optional)
    install_path TEXT NOT NULL,             -- Installation directory
    config_hash TEXT NOT NULL,              -- Hash of build configuration
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,                 -- When build completed/failed
    build_duration INTEGER,                 -- Build duration in seconds
    error_message TEXT                      -- Error message if failed
);
```

### 2. build_configurations (Build-specific configuration details)
```sql
CREATE TABLE build_configurations (
    build_id INTEGER PRIMARY KEY,
    template_version TEXT NOT NULL,         -- Version of template used
    compiler TEXT,                          -- Compiler information
    mpi TEXT,                              -- MPI implementation
    build_flags TEXT,                       -- Additional build flags
    FOREIGN KEY (build_id) REFERENCES builds(id)
);
```

### 3. build_files (Track executables specified in config)
```sql
CREATE TABLE build_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,                -- Relative path from install directory
    file_hash TEXT NOT NULL,                -- SHA256 hash of file
    FOREIGN KEY (build_id) REFERENCES builds(id)
);
```

### 4. build_dependencies (Track build dependencies)
```sql
CREATE TABLE build_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    name TEXT NOT NULL,                     -- Dependency name
    version TEXT NOT NULL,                  -- Version required
    type TEXT NOT NULL,                     -- Type (module, system, etc)
    FOREIGN KEY (build_id) REFERENCES builds(id)
);
```

### 5. build_logs (Store build process logs)
```sql
CREATE TABLE build_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,                    -- Log level (INFO, WARNING, ERROR)
    message TEXT NOT NULL,                  -- Log message
    stage TEXT NOT NULL,                    -- Build stage
    FOREIGN KEY (build_id) REFERENCES builds(id)
);
```

## Key Design Decisions

1. Using SQLite for local storage and simplicity
2. Normalized design with clear relationships
3. Only tracking binaries explicitly specified in build templates
4. Using UUIDs for external references while keeping integer PKs for efficiency
5. Comprehensive logging and error tracking
6. Support for build variants and different configurations

## Common Operations

1. Recording new builds
2. Updating build status
3. Verifying binary integrity
4. Querying build history
5. Finding builds by application/version
6. Tracking build logs and errors

## Questions for Review

1. Is the schema normalized appropriately?
2. Are we missing any critical fields or relationships?
3. Are the data types appropriate?
4. Is there any redundancy we should address?
5. How well will this scale with many builds?
6. Are there any potential performance bottlenecks?
7. How well does this support future extensions? 