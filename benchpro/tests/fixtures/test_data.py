"""
Centralized test data definitions for BenchPRO.

This module contains all standard test profiles, templates, and configurations
that are reused across the test suite.
"""

from typing import Dict, Any


# Standard System Configuration
# =============================

STANDARD_SYSTEM_DATA = {
    "name": "test_system",
    "description": "Test system configuration", 
    "type": "testing",
    "platform": "linux",
    "architecture": "x86_64",
    "environment_type": "test_environment"
}


# Standard Test Profiles
# ======================

STANDARD_APPLICATION_PROFILES = {
    "test_app": {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Standard test application",
        "build": {
            "source": "test_app.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "environment": {
            "modules": ["gcc/11.2.0"],
            "variables": {
                "OMP_NUM_THREADS": "1"
            }
        },
        "job": {
            "scheduler": "local",
            "queue": "compute",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "hello_world.j2"
    },
    
    "merge_test": {
        "task_type": "application",
        "name": "merge_test",
        "version": "2.0",
        "description": "Test application for configuration merging",
        "build": {
            "source": "merge_test.c",
            "compiler": "gcc",
            "flags": "-O3",
            "output": "merge_test",
            "threads": 2
        },
        "environment": {
            "modules": ["gcc/11.2.0", "openmpi/4.1.0"],
            "variables": {
                "OMP_NUM_THREADS": "2"
            }
        },
        "execution": {
            "type": "sched"
        },
        "job": {
            "queue": "test_queue",
            "account": "test_account",
            "nodes": 4,
            "tasks_per_node": 8,
            "time_limit": "01:00:00"
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "hello_world.j2"
    },
    
    "cli_test": {
        "task_type": "application",
        "name": "cli_test",
        "version": "1.0",
        "description": "Test application for CLI overrides",
        "build": {
            "source": "cli_test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "cli_test",
            "threads": 1
        },
        "environment": {
            "modules": ["gcc/11.2.0"],
            "variables": {}
        },
        "execution": {
            "type": "sched"
        },
        "job": {
            "queue": "compute",
            "account": "project123",
            "nodes": 2,
            "tasks_per_node": 16,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "hello_world.j2"
    },
    
    "test_profile": {
        "task_type": "application",
        "name": "test_profile",
        "version": "1.0",
        "description": "Generic test profile",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "execution": {
            "type": "sched"
        },
        "job": {
            "queue": "compute",
            "account": "project123",
            "nodes": 2,
            "tasks_per_node": 16,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "hello_world.j2"
    }
}

STANDARD_BENCHMARK_PROFILES = {
    "test_benchmark": {
        "task_type": "benchmark",
        "name": "test_benchmark",
        "version": "1.0",
        "description": "Standard test benchmark",
        "run": {
            "executable": "test_app",
            "arguments": "--test",
            "input_files": ["input.dat"],
            "output_files": ["output.dat"],
            "threads": 1
        },
        "requirements": {
            "application": "test_app",
            "version": "1.0"
        },
        "environment": {
            "modules": ["gcc/11.2.0"],
            "variables": {
                "OMP_NUM_THREADS": "1"
            }
        },
        "execution": {
            "type": "local"
        },
        "job": {
            "queue": "compute",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "input_dir": "input",
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": True,
            "keep_output": True
        },
        "results": {
            "metrics": ["runtime"],
            "parser": "simple",
            "output_format": "json"
        },
        "template": "hello_world.j2"
    },
    
    "orchestrator_test_profile": {
        "task_type": "benchmark",
        "name": "orchestrator_test_profile",
        "version": "1.0",
        "description": "Test profile for orchestrator tests",
        "run": {
            "executable": "test_binary",
            "arguments": "--benchmark",
            "input_files": [],
            "output_files": ["results.out"],
            "threads": 1
        },
        "requirements": {
            "application": "test_app",
            "version": "1.0"
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "execution": {
            "type": "local"
        },
        "job": {
            "queue": "default",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:05:00"
        },
        "workspace": {
            "input_dir": "input",
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": True,
            "keep_output": True
        },
        "template": "vanilla.j2"
    },
    
    "factory_test_profile": {
        "task_type": "benchmark",
        "name": "factory_test_profile",
        "version": "1.0",
        "description": "Test profile for factory tests",
        "run": {
            "executable": "test_exec",
            "application": "test_app",
            "arguments": "",
            "input_files": [],
            "output_files": [],
            "threads": 1
        },
        "requirements": {
            "application": "test_app",
            "version": "1.0"
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "execution": {
            "type": "local"
        },
        "job": {
            "queue": "default",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:05:00"
        },
        "workspace": {
            "input_dir": "input",
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": True,
            "keep_output": True
        },
        "template": "test.j2"
    },
    
    "golden_path_profile": {
        "task_type": "benchmark",
        "name": "golden_path_profile",
        "version": "1.0",
        "description": "Golden path test profile",
        "run": {
            "executable": "some_app",
            "application": "some_app",
            "arguments": "--run",
            "input_files": [],
            "output_files": ["output.txt"],
            "threads": 1
        },
        "requirements": {
            "application": "some_app",
            "version": "1.0"
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "execution": {
            "type": "local"
        },
        "job": {
            "queue": "default",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:05:00"
        },
        "workspace": {
            "input_dir": "input",
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": True,
            "keep_output": True
        },
        "template": "vanilla.j2"
    }
}

# Standard Test Templates
# =======================

STANDARD_TEMPLATES = {
    "hello_world.j2": """#!/bin/bash

# Get the workspace root directory (directory containing this script)
SCRIPT_PATH=$0
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
# Change to workspace root directory
cd "$SCRIPT_DIR"
echo "Working in workspace: $SCRIPT_DIR"

# Load required modules
{% if environment and environment.modules %}
{% for module in environment.modules %}
{% if module is string %}
module load {{ module }}
{% else %}
module load {{ module.name }}{% if module.version %}/{{ module.version }}{% endif %}
{% endif %}
{% endfor %}
{% endif %}

# Set environment variables
{% if environment and environment.variables %}
{% for var, value in environment.variables.items() %}
export {{ var }}="{{ value }}"
{% endfor %}
{% endif %}

echo "Job started at: `date +"%Y-%m-%d %H:%M:%S"`"
echo "--------------------------------------"

echo "Working in `pwd`"

# Print system information
echo "Running on system: {{ system.name | default('default') }} ({{ system.description | default('Default system configuration') }})"
echo "System type: {{ system.type | default('unknown') }}"
echo "Environment type: {{ system.name | default('default') }}"

{% if task_type == 'application' %}
# Build the application
echo "Building application: {{ name }} {{ version }}"
{{ build.compiler }} {{ build.flags }} -o {{ build.output }} {{ build.source }}
{% elif task_type == 'benchmark' %}
# Run the benchmark
echo "Running benchmark: {{ name }} {{ version }}"
{% if run.executable %}
{{ run.executable }} {{ run.arguments | default('') }}
{% endif %}
{% endif %}

echo "--------------------------------------"
echo "Job ended at: `date +"%Y-%m-%d %H:%M:%S"`"
""",

    "vanilla.j2": """#!/bin/bash
{{ command | default('echo "No command specified"') }}
""",

    "test.j2": """#!/bin/bash
# Test template for {{ name }}
echo "Executing test: {{ name }}"
{% if run and run.executable %}
{{ run.executable }} {{ run.arguments | default('') }}
{% endif %}
echo "Test completed"
""",

    "test_app.j2": """#!/bin/bash
# Application build script for {{ name }}
echo "Building {{ name }} v{{ version }}..."
{{ build.compiler }} {{ build.flags }} -o {{ build.output }} {{ build.source }}
echo "Build complete."
""",

    "test_template.j2": """#!/bin/bash
#SBATCH --job-name={{ job.name }}
#SBATCH --time={{ job.time_limit }}

echo "Running {{ job.name }}"
{{ application.executable }} {{ application.arguments }}
"""
}

# Standard Test Configurations
# =============================

STANDARD_DEFAULT_CONFIG = {
    "task_type": "application",
    "name": "default_app",
    "version": "1.0",
    "description": "Default application",
    "build": {
        "source": "default.c",
        "compiler": "gcc",
        "flags": "-O2",
        "output": "default_app",
        "threads": 1
    },
    "environment": {
        "modules": [],
        "variables": {}
    },
    "execution": {
        "type": "local"
    },
    "job": {
        "queue": "compute",
        "account": "default_account",
        "nodes": 1,
        "tasks_per_node": 1,
        "time_limit": "00:10:00"
    },
    "workspace": {
        "source_dir": "/path/to/source",
        "build_dir": "build",
        "logs_dir": "logs",
        "keep_source": True,
        "keep_build": True
    },
    "template": "default_app.j2"
}

STANDARD_SYSTEM_CONFIG = {
    "system": STANDARD_SYSTEM_DATA,
    "environment": {
        "variables": {
            "SYSTEM_TYPE": "test_environment"
        }
    },
    "execution": {
        "type": "local"
    },
    "job": {
        "queue": "compute",
        "account": "system_account",
        "nodes": 1,
        "tasks_per_node": 16,
        "time_limit": "00:10:00"
    }
}

# Standard Test Source Files
# ==========================

STANDARD_SOURCE_FILES = {
    "hello_world.c": """#include <stdio.h>
int main() {
    printf("Hello, world!\\n");
    return 0;
}
""",
    
    "test_app.c": """#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    printf("Test application running...\\n");
    if (argc > 1) {
        printf("Arguments: %s\\n", argv[1]);
    }
    printf("Test completed successfully\\n");
    return 0;
}
""",
    
    "merge_test.c": """#include <stdio.h>
int main() {
    printf("Merge test application\\n");
    return 0;
}
""",
    
    "cli_test.c": """#include <stdio.h>
int main() {
    printf("CLI test application\\n");
    return 0;
}
"""
}


# Utility Functions for Test Data Management
# ==========================================

def get_standard_application_profile(name: str) -> Dict[str, Any]:
    """Get a standard application profile by name."""
    if name not in STANDARD_APPLICATION_PROFILES:
        raise ValueError(f"Unknown application profile: {name}")
    return STANDARD_APPLICATION_PROFILES[name].copy()


def get_standard_benchmark_profile(name: str) -> Dict[str, Any]:
    """Get a standard benchmark profile by name."""
    if name not in STANDARD_BENCHMARK_PROFILES:
        raise ValueError(f"Unknown benchmark profile: {name}")
    return STANDARD_BENCHMARK_PROFILES[name].copy()


def get_standard_template(name: str) -> str:
    """Get a standard template by name."""
    if name not in STANDARD_TEMPLATES:
        raise ValueError(f"Unknown template: {name}")
    return STANDARD_TEMPLATES[name]


def get_standard_source_file(name: str) -> str:
    """Get a standard source file by name."""
    if name not in STANDARD_SOURCE_FILES:
        raise ValueError(f"Unknown source file: {name}")
    return STANDARD_SOURCE_FILES[name]


def get_standard_system_data() -> Dict[str, Any]:
    """Get the standard system configuration data."""
    return STANDARD_SYSTEM_DATA.copy()


def get_all_standard_profiles() -> Dict[str, Dict[str, Any]]:
    """Get all standard profiles (applications and benchmarks)."""
    return {
        **STANDARD_APPLICATION_PROFILES,
        **STANDARD_BENCHMARK_PROFILES
    } 