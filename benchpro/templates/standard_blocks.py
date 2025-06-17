"""
Standard template blocks for BenchPRO.

This module provides standard template blocks for common script components
like shebang lines, SLURM directives, workspace handling, etc.
"""

from typing import Dict, Any

from benchpro.templates.blocks import StringTemplateBlock
from benchpro.templates.composition import TemplateCompositionEngine
from benchpro.utils.logger import get_logger

logger = get_logger(__name__)

# Block priorities - lower numbers come first
PRIORITY_SHEBANG = 10
PRIORITY_HEADER_COMMENTS = 15
PRIORITY_SLURM_DIRECTIVES = 20
PRIORITY_WORKSPACE_DIR = 30
PRIORITY_MODULE_LOADING = 40
PRIORITY_ENV_VARS = 50
PRIORITY_START_TIMESTAMP = 60
PRIORITY_USER_COMMANDS = 100
PRIORITY_END_TIMESTAMP = 900
PRIORITY_FOOTER = 1000

# Shebang block - used in all scripts
SHEBANG_BLOCK = StringTemplateBlock(
    name="shebang",
    content="#!/bin/bash",
    priority=PRIORITY_SHEBANG,
    description="Bash shell interpreter directive"
)

# SLURM directives block - only used for SLURM execution
SLURM_DIRECTIVES_BLOCK = StringTemplateBlock(
    name="slurm_directives",
    content="""#SBATCH -J {{ job.name }}
{% if job.nodes %}#SBATCH -N {{ job.nodes }}
{% endif %}{% if job.tasks_per_node %}#SBATCH --ntasks-per-node={{ job.tasks_per_node }}
{% endif %}{% if job.time_limit %}#SBATCH -t {{ job.time_limit }}
{% endif %}{% if job.queue %}#SBATCH -p {{ job.queue }}
{% endif %}{% if job.account %}#SBATCH -A {{ job.account }}
{% endif %}{% if job.name and workspace and workspace.logs_dir %}#SBATCH -o {{ workspace.logs_dir }}/{{ job.name }}.%j.out
#SBATCH -e {{ workspace.logs_dir }}/{{ job.name }}.%j.err
{% endif %}""",
    priority=PRIORITY_SLURM_DIRECTIVES,
    description="SLURM job scheduler directives",
    contexts=["slurm"]
)

# Workspace directory block - used in all scripts
WORKSPACE_DIR_BLOCK = StringTemplateBlock(
    name="workspace_dir",
    content="""# Get the workspace root directory (directory containing this script)
SCRIPT_PATH=$0
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
# Change to workspace root directory
cd "$SCRIPT_DIR"
echo "Working in workspace: $SCRIPT_DIR"
""",
    priority=PRIORITY_WORKSPACE_DIR,
    description="Workspace directory handling code"
)

# Module loading block - used in all scripts
MODULE_LOADING_BLOCK = StringTemplateBlock(
    name="module_loading",
    content="""# Load required modules
{% if environment and environment.module_paths %}
# Add custom module paths
{% for path in environment.module_paths %}
module use {{ path }}
{% endfor %}
{% endif %}

{% if environment and environment.modules %}
# Load modules with versions
{% for module in environment.modules %}
{% if module is mapping and module.name %}
{% if module.version %}
module load {{ module.name }}/{{ module.version }}
{% else %}
module load {{ module.name }}
{% endif %}
{% else %}
module load {{ module }}
{% endif %}
{% endfor %}
{% endif %}
""",
    priority=PRIORITY_MODULE_LOADING,
    description="Module loading commands"
)

# Environment variables block - used in all scripts
ENV_VARS_BLOCK = StringTemplateBlock(
    name="env_vars",
    content="""# Set environment variables
{% if env %}
{% for key, value in env.items() %}
export {{ key }}={{ value }}
{% endfor %}
{% endif %}
""",
    priority=PRIORITY_ENV_VARS,
    description="Environment variable setup"
)

# Start timestamp block - used in all scripts
START_TIMESTAMP_BLOCK = StringTemplateBlock(
    name="start_timestamp",
    content="""echo "Job started at: `date +"%Y-%m-%d %H:%M:%S"`"
echo "----------------------------------------"
""",
    priority=PRIORITY_START_TIMESTAMP,
    description="Start time logging"
)

# End timestamp block - used in all scripts
END_TIMESTAMP_BLOCK = StringTemplateBlock(
    name="end_timestamp",
    content="""echo "----------------------------------------"
echo "Job ended at: `date +"%Y-%m-%d %H:%M:%S"`"
""",
    priority=PRIORITY_END_TIMESTAMP,
    description="End time logging"
)


def register_standard_blocks(engine: TemplateCompositionEngine, execution_context: str) -> None:
    """
    Register standard blocks with a template composition engine.
    
    Args:
        engine: The template composition engine to register blocks with.
        execution_context: The execution context for determining which blocks to register.
    """
    logger.debug(f"Registering standard blocks for execution context: {execution_context}")
    
    # Always register the shebang block
    engine.register_block(SHEBANG_BLOCK)
    
    # Register SLURM directives only for SLURM execution context
    if execution_context.lower() == "slurm":
        engine.register_block(SLURM_DIRECTIVES_BLOCK)
    
    # Register common blocks for all execution contexts
    engine.register_block(WORKSPACE_DIR_BLOCK)
    engine.register_block(MODULE_LOADING_BLOCK)
    engine.register_block(ENV_VARS_BLOCK)
    engine.register_block(START_TIMESTAMP_BLOCK)
    engine.register_block(END_TIMESTAMP_BLOCK)
    
    logger.debug("Standard blocks registered successfully") 