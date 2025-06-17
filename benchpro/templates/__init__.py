"""
Template systems for BenchPRO.

This package provides template handling and script generation functionality.
"""

# Export main classes
from benchpro.templates.blocks import (
    TemplateBlock, 
    StringTemplateBlock, 
    FileTemplateBlock, 
    FunctionTemplateBlock,
    TemplateError
)
from benchpro.templates.composition import TemplateCompositionEngine
from benchpro.templates.standard_blocks import (
    SHEBANG_BLOCK,
    SLURM_DIRECTIVES_BLOCK,
    WORKSPACE_DIR_BLOCK,
    MODULE_LOADING_BLOCK,
    ENV_VARS_BLOCK,
    START_TIMESTAMP_BLOCK,
    END_TIMESTAMP_BLOCK,
    register_standard_blocks
)
from benchpro.templates.script_generators import (
    ComposableScriptGenerator,
    LocalScriptGenerator,
    SlurmScriptGenerator
)
