import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))

project = 'BenchPRO-NG'
copyright = '2025, BenchPRO Team'
author = 'BenchPRO Team'
release = '0.1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_click',
    'sphinx_rtd_theme',
]

templates_path = ['_templates']
exclude_patterns = ['../dev']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
