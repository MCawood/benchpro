"""
Configuration schema package for BenchPRO.

This package contains schema definitions for validating configuration files.
"""

from benchpro.config.schema.application import ApplicationSchema
from benchpro.config.schema.benchmark import BenchmarkSchema

__all__ = ["ApplicationSchema", "BenchmarkSchema"] 