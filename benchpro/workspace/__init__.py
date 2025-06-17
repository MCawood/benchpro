"""
Workspace management package for BenchPRO.

This package provides functionality for managing workspaces for BenchPRO tasks.
"""

from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.workspace.module_manager import ModuleManager, ModuleError

__all__ = ['WorkspaceManager', 'ModuleManager', 'ModuleError'] 