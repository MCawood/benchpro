"""
Results module for BenchPRO.

This module handles capturing job output, extracting metrics, and storing results.
"""

from benchpro.results.result_capture import ResultCapture
from benchpro.results.result_extractor import ResultExtractor

__all__ = ['ResultCapture', 'ResultExtractor']
