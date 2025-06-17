# Parameter Report Feature Implementation

## Overview

This document outlines the implementation of a parameter report feature for BenchPRO that allows users to see all configuration parameters and their origins during application builds and benchmark runs.

## Problem Statement

Users often struggle to understand where configuration values are coming from when troubleshooting BenchPRO tasks. Currently, the system merges configuration from multiple sources (defaults, system configs, profiles, CLI overrides, smart defaults) but provides no visibility into:

- Which source provided each final parameter value
- How parameter precedence is being applied
- What the final merged configuration looks like before task execution
- Whether CLI overrides are working as expected

This lack of transparency makes debugging configuration issues difficult and reduces user confidence in the system.

## Requirements

### Functional Requirements

1. **Parameter Origin Tracking**: Track the source of every configuration parameter
2. **CLI Integration**: Add `--param-report` flag to `build` and `bench` commands
3. **Dry Run Compatibility**: Work seamlessly with `--dry-run` to show what would be used without execution
4. **Human-Readable Output**: Present information in a clear, structured format
5. **Complete Coverage**: Include all configuration sources in the report

### Non-Functional Requirements

1. **Performance**: Minimal impact on normal execution when feature is not used
2. **Maintainability**: Clean separation of concerns, reusable components
3. **Extensibility**: Easy to add new configuration sources or output formats

## Current Configuration Architecture Review

### Configuration Flow

```
1. Default Config (benchpro/config/default.yaml)
2. System Config (user/.benchpro/config/system/[name].yaml) 
3. Profile Config (user/.benchpro/inputs/[type]/[profile].yaml)
4. CLI Overrides (from command line parameters)
5. Smart Defaults (automatic scheduler settings)
6. Variable Resolution (template substitution)
7. Validation (schema enforcement)
```

### Key Components

- **ConfigManager**: Orchestrates the configuration loading and merging process
- **HierarchicalConfigMerger**: Performs deep merging of configuration dictionaries
- **YamlConfigLoader**: Loads configuration files from various sources
- **TemplateVariableResolver**: Resolves template variables in configuration values
- **ConfigValidator**: Validates final configuration against schemas

### Current Limitations

1. **No Origin Tracking**: The merger only preserves final values, not sources
2. **Single Pass Processing**: Configuration is processed once without intermediate tracking
3. **Limited Introspection**: No mechanism to inspect the merge process

## Solution Architecture

### 1. Configuration Metadata System

Introduce a parallel metadata tracking system that preserves origin information alongside configuration values.

#### Data Structure Design

```python
@dataclass
class ConfigValue:
    """Represents a configuration value with origin metadata."""
    value: Any
    source: str          # e.g., "default", "system:slurm", "profile:hello_world", "cli", "smart_defaults"
    source_file: Optional[str]  # File path for file-based sources
    line_number: Optional[int]  # Line number for YAML sources
    precedence: int      # Numeric precedence for sorting
    applied_at: str      # Timestamp when value was applied

@dataclass 
class ConfigReport:
    """Complete configuration report with metadata."""
    final_config: Dict[str, Any]           # Final merged configuration
    config_metadata: Dict[str, ConfigValue]  # Metadata for each config path
    merge_history: List[MergeStep]         # Step-by-step merge history
    profile_name: str
    cli_overrides: Dict[str, Any]
    generation_time: str
    
@dataclass
class MergeStep:
    """Represents a single step in the configuration merge process."""
    step_name: str       # e.g., "Loading default config", "Applying CLI overrides"
    source: str          # Source identifier
    changes: Dict[str, Any]  # Configuration changes in this step
    timestamp: str
```

### 2. Enhanced Configuration Components

#### TrackedConfigMerger

Extend `HierarchicalConfigMerger` to track origin metadata:

```python
class TrackedConfigMerger(HierarchicalConfigMerger):
    """Configuration merger that tracks value origins."""
    
    def merge_with_tracking(self, configs: List[Tuple[Dict[str, Any], str]]) -> ConfigReport:
        """
        Merge configurations while tracking origins.
        
        Args:
            configs: List of (config_dict, source_name) tuples
            
        Returns:
            ConfigReport with complete tracking information
        """
        # Implementation tracks each merge step and maintains metadata
```

#### ConfigReportGenerator

New component responsible for generating human-readable reports:

```python
class ConfigReportGenerator:
    """Generates formatted configuration reports."""
    
    def generate_report(self, report: ConfigReport, format: str = "table") -> str:
        """Generate formatted report from ConfigReport data."""
        
    def generate_table_report(self, report: ConfigReport) -> str:
        """Generate table-formatted report."""
        
    def generate_json_report(self, report: ConfigReport) -> str:
        """Generate JSON-formatted report."""
        
    def generate_yaml_report(self, report: ConfigReport) -> str:
        """Generate YAML-formatted report."""
```

### 3. CLI Integration

#### New Command Line Options

Add `--param-report` option to both `build` and `bench` commands:

```python
@click.option(
    "--param-report",
    is_flag=True,
    help="Display detailed parameter report showing configuration sources and values."
)
@click.option(
    "--param-report-format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Format for parameter report output."
)
```

#### Integration Points

1. **Early Integration**: Generate report after configuration merging but before task creation
2. **Conditional Execution**: When `--param-report` is used with `--dry-run`, only show report and exit
3. **Normal Execution**: When `--param-report` is used alone, show report then continue with task execution

### 4. Report Format Design

#### Table Format (Default)

```
BenchPRO Parameter Report
=========================
Profile: hello_world
Task Type: application
Generated: 2024-01-15 14:30:22

Configuration Parameters:
┌─────────────────────────┬─────────────────┬──────────────────────┬─────────────────────────────┐
│ Parameter               │ Value           │ Source               │ Source File                 │
├─────────────────────────┼─────────────────┼──────────────────────┼─────────────────────────────┤
│ task_type               │ application     │ cli                  │ --                          │
│ execution.type          │ local           │ smart_defaults       │ --                          │
│ job.scheduler           │ local           │ smart_defaults       │ --                          │
│ job.queue               │ compute         │ profile:hello_world  │ hello_world.yaml:15         │
│ job.time_limit          │ 00:10:00        │ default              │ default.yaml:23             │
│ build.compiler          │ gcc             │ profile:hello_world  │ hello_world.yaml:8          │
│ build.flags             │ -O2             │ system:slurm         │ system/slurm.yaml:12        │
│ workspace.output_dir    │ /custom/path    │ cli                  │ --                          │
└─────────────────────────┴─────────────────┴──────────────────────┴─────────────────────────────┘

Configuration Sources:
├─ default: /path/to/benchpro/config/default.yaml
├─ system:slurm: ~/.benchpro/config/system/slurm.yaml  
├─ profile:hello_world: ~/.benchpro/inputs/application/hello_world.yaml
├─ cli: Command line arguments
└─ smart_defaults: Automatic configuration defaults

Merge History:
1. Loading default configuration (23 parameters)
2. Loading system configuration: slurm (7 parameters, 3 overrides)
3. Loading profile configuration: hello_world (12 parameters, 5 overrides)
4. Applying CLI overrides (3 parameters, 2 overrides)
5. Applying smart defaults (2 parameters, 1 override)

Final configuration contains 47 parameters from 5 sources.
```

#### JSON Format

```json
{
  "profile_name": "hello_world",
  "task_type": "application", 
  "generation_time": "2024-01-15T14:30:22Z",
  "final_config": { ... },
  "parameter_metadata": {
    "task_type": {
      "value": "application",
      "source": "cli",
      "precedence": 4,
      "applied_at": "2024-01-15T14:30:22Z"
    },
    "execution.type": {
      "value": "local",
      "source": "smart_defaults", 
      "precedence": 5,
      "applied_at": "2024-01-15T14:30:22Z"
    }
  },
  "merge_history": [ ... ],
  "source_files": { ... }
}
```

## Implementation Plan

### Phase 1: Core Infrastructure

1. **Create ConfigValue and ConfigReport data structures**
   - Define dataclasses in `benchpro/config/metadata.py`
   - Add type hints and documentation

2. **Implement TrackedConfigMerger**
   - Extend existing HierarchicalConfigMerger
   - Add metadata tracking to merge operations
   - Maintain backward compatibility

3. **Create ConfigReportGenerator**
   - Implement table, JSON, and YAML formatters
   - Add formatting utilities for complex nested structures

### Phase 2: ConfigManager Integration

1. **Enhance ConfigManager**
   - Add `get_complete_config_with_tracking()` method
   - Integrate TrackedConfigMerger for report generation
   - Maintain existing API for backward compatibility

2. **Update configuration loading**
   - Modify loaders to provide source metadata
   - Add file path and line number tracking for YAML sources

### Phase 3: CLI Integration

1. **Add CLI options**
   - Extend `build` and `bench` commands with `--param-report` options
   - Implement report generation in command handlers

2. **Integrate with TaskOrchestrator**
   - Add parameter report generation before task creation
   - Handle dry-run mode combinations

### Phase 4: Testing and Documentation

1. **Comprehensive testing**
   - Unit tests for all new components
   - Integration tests for CLI functionality
   - Test various configuration scenarios

2. **Documentation updates**
   - User guide for parameter report feature
   - API documentation for new components
   - Examples and troubleshooting guides

## Implementation Details

### Key Files to Modify

```
benchpro/config/
├── metadata.py           # NEW: Data structures for tracking
├── tracked_merger.py     # NEW: TrackedConfigMerger implementation  
├── report_generator.py   # NEW: Report formatting
├── config_manager.py     # MODIFY: Add tracking methods
└── merger.py            # MODIFY: Add metadata hooks

benchpro/cli/
└── cli.py               # MODIFY: Add --param-report options

benchpro/executor/
└── task_orchestrator.py # MODIFY: Add report generation
```

### Configuration File Enhancements

No changes to existing configuration file formats are required. The feature works by adding metadata tracking to the existing configuration loading and merging process.

### Performance Considerations

1. **Lazy Evaluation**: Only track metadata when `--param-report` is specified
2. **Memory Efficiency**: Use lightweight metadata structures
3. **Minimal Overhead**: Ensure normal execution path remains fast

## Future Enhancements

### Phase 5: Advanced Features (Future)

1. **Interactive Report**: Web-based interface for exploring configuration
2. **Configuration Diff**: Compare configurations between profiles or runs  
3. **Export Options**: Save reports to files for analysis
4. **Integration Points**: API for external tools to access configuration metadata

### Potential Extensions

1. **Configuration Validation Report**: Show which parameters passed/failed validation
2. **Variable Resolution Tracking**: Show template variable substitution details
3. **Schema Information**: Include schema validation details in reports
4. **Historical Comparison**: Compare current configuration with previous runs

## Success Criteria

1. **Functionality**: Users can easily identify configuration parameter sources
2. **Usability**: Report format is clear and actionable for troubleshooting
3. **Performance**: Minimal impact on normal execution (< 5% overhead when not used)
4. **Compatibility**: No breaking changes to existing functionality
5. **Adoption**: Feature reduces configuration-related support requests

## Risk Mitigation

1. **Backward Compatibility**: All existing APIs remain unchanged
2. **Performance Impact**: Feature is opt-in and optimized for minimal overhead
3. **Code Complexity**: Clean abstraction layers prevent architectural pollution
4. **Test Coverage**: Comprehensive testing ensures reliability

## Conclusion

The parameter report feature will significantly improve BenchPRO's usability by providing transparency into configuration merging. The proposed architecture maintains clean separation of concerns while adding powerful introspection capabilities that will help users understand and debug their configurations more effectively. 