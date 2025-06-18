"""
Configuration Report Generator for BenchPRO.

This module provides functionality for generating formatted configuration reports
in various formats (table, JSON, YAML) from ConfigReport data structures.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from benchpro.config.metadata import ConfigReport, ConfigValue, MergeStep


class ConfigReportGenerator:
    """
    Generates formatted configuration reports from ConfigReport data.
    
    Supports multiple output formats:
    - table: Human-readable table format (default)
    - json: Machine-readable JSON format
    - yaml: Human and machine-readable YAML format
    """
    
    def __init__(self):
        """Initialize the report generator."""
        pass
    
    def generate_report(self, report: ConfigReport, format_type: str = "table") -> str:
        """
        Generate a formatted report from ConfigReport data.
        
        Args:
            report: ConfigReport instance to format.
            format_type: Output format ("table", "json", or "yaml").
            
        Returns:
            Formatted report string.
            
        Raises:
            ValueError: If format_type is not supported.
        """
        if format_type == "table":
            return self.generate_table_report(report)
        elif format_type == "json":
            return self.generate_json_report(report)
        elif format_type == "yaml":
            return self.generate_yaml_report(report)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    def generate_table_report(self, report: ConfigReport) -> str:
        """
        Generate a human-readable table format report.
        
        Args:
            report: ConfigReport instance to format.
            
        Returns:
            Table-formatted report string.
        """
        lines = []
        
        # Header
        lines.append("BenchPRO Parameter Report")
        lines.append("=" * 25)
        lines.append(f"Profile: {report.profile_name}")
        
        # Extract task type from final config
        task_type = report.final_config.get("task_type", "unknown")
        lines.append(f"Task Type: {task_type}")
        lines.append(f"Generated: {self._format_timestamp(report.generation_time)}")
        lines.append("")
        
        # Configuration Parameters Table
        lines.append("Configuration Parameters:")
        lines.extend(self._generate_parameters_table(report))
        lines.append("")
        
        # Configuration Sources
        lines.append("Configuration Sources:")
        lines.extend(self._generate_sources_list(report))
        lines.append("")
        
        # Merge History
        lines.append("Merge History:")
        lines.extend(self._generate_merge_history(report))
        lines.append("")
        
        # Summary
        total_params = len(report.config_metadata)
        source_count = len(report.get_source_summary())
        lines.append(f"Final configuration contains {total_params} parameters from {source_count} sources.")
        
        return "\n".join(lines)
    
    def generate_json_report(self, report: ConfigReport) -> str:
        """
        Generate a JSON format report.
        
        Args:
            report: ConfigReport instance to format.
            
        Returns:
            JSON-formatted report string.
        """
        return report.to_json(indent=2)
    
    def generate_yaml_report(self, report: ConfigReport) -> str:
        """
        Generate a YAML format report.
        
        Args:
            report: ConfigReport instance to format.
            
        Returns:
            YAML-formatted report string.
        """
        return report.to_yaml()
    
    def _generate_parameters_table(self, report: ConfigReport) -> List[str]:
        """
        Generate the parameters table section using tabulate for dynamic sizing.
        
        Args:
            report: ConfigReport instance.
            
        Returns:
            List of table lines.
        """
        # Prepare table data
        headers = ["Parameter", "Value", "Source"]
        table_data = []
        
        # Parameter rows (sorted by parameter name for consistency)
        sorted_params = sorted(report.config_metadata.items())
        
        for param_path, config_value in sorted_params:
            # Format combined source information
            combined_source = self._format_combined_source(config_value)
            
            # Ensure value is properly formatted as string
            value_str = self._format_value_for_display(config_value.value)
            
            table_data.append([
                param_path,
                value_str,
                combined_source
            ])
        
        # Generate table with dynamic column sizing (better than tabulate for our use case)
        lines = []
        
        # Calculate optimal column widths
        param_width = max(len("Parameter"), max(len(row[0]) for row in table_data))
        value_width = min(50, max(len("Value"), max(len(row[1]) for row in table_data)))  # Cap at 50 chars
        source_width = max(len("Source"), max(len(row[2]) for row in table_data))
        
        # Ensure reasonable minimum widths
        param_width = max(param_width, 20)
        value_width = max(value_width, 15)
        source_width = max(source_width, 25)
        
        # Create header
        lines.append(f"{'Parameter':<{param_width}} {'Value':<{value_width}} {'Source':<{source_width}}")
        lines.append("-" * (param_width + value_width + source_width + 2))
        
        # Add data rows
        for param, value, source in table_data:
            # Truncate value if too long
            display_value = value if len(value) <= value_width else value[:value_width-3] + "..."
            lines.append(f"{param:<{param_width}} {display_value:<{value_width}} {source:<{source_width}}")
        
        return lines
    

    
    def _format_combined_source(self, config_value: ConfigValue) -> str:
        """
        Format combined source information (source + file).
        
        Args:
            config_value: ConfigValue instance with metadata.
            
        Returns:
            Combined source string.
        """
        base_source = config_value.source
        
        # For file-based sources, add filename in parentheses
        if config_value.source_file:
            filename = self._get_filename(config_value.source_file)
            if config_value.line_number:
                return f"{base_source} ({filename}:{config_value.line_number})"
            else:
                return f"{base_source} ({filename})"
        
        # For non-file sources, just return the source
        return base_source
    
    def _format_value_for_display(self, value: Any) -> str:
        """
        Format a configuration value for display in the table.
        
        Args:
            value: Configuration value of any type.
            
        Returns:
            String representation suitable for table display.
        """
        if isinstance(value, bool):
            return str(value)
        elif isinstance(value, (list, tuple)):
            # Format lists/tuples in a compact way
            return str(value)
        elif isinstance(value, dict):
            # Format dictionaries in a compact way
            return str(value)
        elif value is None:
            return "None"
        else:
            return str(value)
    
    def _generate_sources_list(self, report: ConfigReport) -> List[str]:
        """
        Generate the configuration sources list.
        
        Args:
            report: ConfigReport instance.
            
        Returns:
            List of source lines.
        """
        lines = []
        
        # Collect unique sources from metadata
        sources = {}
        for config_value in report.config_metadata.values():
            source = config_value.source
            if source not in sources:
                sources[source] = config_value.source_file or "--"
        
        # Format sources list
        for i, (source, source_file) in enumerate(sorted(sources.items())):
            prefix = "├─" if i < len(sources) - 1 else "└─"
            if source_file != "--":
                lines.append(f"{prefix} {source}: {source_file}")
            else:
                lines.append(f"{prefix} {source}: Command line arguments" if source == "cli" 
                           else f"{prefix} {source}: Automatic configuration defaults")
        
        return lines
    
    def _generate_merge_history(self, report: ConfigReport) -> List[str]:
        """
        Generate the merge history section.
        
        Args:
            report: ConfigReport instance.
            
        Returns:
            List of merge history lines.
        """
        lines = []
        
        for i, step in enumerate(report.merge_history, 1):
            # Count changes
            change_count = len(step.changes)
            override_info = ""
            if step.parameters_modified > 0:
                override_info = f", {step.parameters_modified} overrides"
            
            lines.append(f"{i}. {step.step_name} ({change_count} parameters{override_info})")
        
        return lines
    

    
    def _get_filename(self, file_path: str) -> str:
        """
        Extract filename from a file path.
        
        Args:
            file_path: Full file path.
            
        Returns:
            Just the filename portion.
        """
        return file_path.split("/")[-1] if file_path else ""
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """
        Format an ISO timestamp for display.
        
        Args:
            timestamp_str: ISO format timestamp string.
            
        Returns:
            Human-readable timestamp.
        """
        try:
            # Parse the ISO timestamp
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            # If parsing fails, return the original string
            return timestamp_str


class ParameterReportDisplay:
    """
    Helper class for displaying parameter reports in different contexts.
    
    This class provides convenience methods for displaying reports with
    appropriate formatting and handling different output scenarios.
    """
    
    def __init__(self, generator: Optional[ConfigReportGenerator] = None):
        """
        Initialize the display helper.
        
        Args:
            generator: ConfigReportGenerator instance. If None, creates a new one.
        """
        self.generator = generator or ConfigReportGenerator()
    
    def display_report(self, report: ConfigReport, format_type: str = "table", 
                      show_dry_run_notice: bool = False) -> None:
        """
        Display a parameter report to stdout.
        
        Args:
            report: ConfigReport to display.
            format_type: Format for display ("table", "json", "yaml").
            show_dry_run_notice: Whether to show a dry-run notice.
        """
        if show_dry_run_notice:
            print("DRY RUN: Configuration report (no task execution)")
            print()
        
        formatted_report = self.generator.generate_report(report, format_type)
        print(formatted_report)
    
    def should_display_report(self, param_report_flag: bool, dry_run_flag: bool) -> bool:
        """
        Determine if a parameter report should be displayed.
        
        Args:
            param_report_flag: Whether --param-report was specified.
            dry_run_flag: Whether --dry-run was specified.
            
        Returns:
            True if report should be displayed.
        """
        return param_report_flag
    
    def should_continue_execution(self, param_report_flag: bool, dry_run_flag: bool) -> bool:
        """
        Determine if execution should continue after displaying report.
        
        Args:
            param_report_flag: Whether --param-report was specified.
            dry_run_flag: Whether --dry-run was specified.
            
        Returns:
            True if execution should continue.
        """
        # If both flags are set, only show report and exit
        if param_report_flag and dry_run_flag:
            return False
        # Otherwise, continue with normal execution
        return True 