"""
Result extraction strategies for BenchPRO.

This package contains different strategies for extracting benchmark results.
"""

from .base import BaseExtractor
from .regex import RegexExtractor
from .command import CommandExtractor

__all__ = ['BaseExtractor', 'RegexExtractor', 'CommandExtractor'] 