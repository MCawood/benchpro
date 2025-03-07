"""
Variable Resolver for BenchPRO.

This module provides functionality for substituting variables in configuration values.
"""

import os
import re
import yaml
import copy
from typing import Dict, Any, List, Optional, Match, Pattern, Callable

from benchpro.utils.logger import get_logger
from benchpro.config.interfaces import VariableResolverInterface


class TemplateVariableResolver(VariableResolverInterface):
    """
    Substitutes variables in configuration values.
    
    Responsibilities:
    - Substitute variables in configuration values
    - Handle environment variables
    - Handle recursive variable references
    """
    
    # Regular expression for variable references
    VAR_PATTERN = re.compile(r'\${([^}]+)}')
    
    def __init__(self, max_passes: int = 10):
        """
        Initialize the TemplateVariableResolver.
        
        Args:
            max_passes: Maximum number of passes to make when resolving variables.
                      This prevents infinite loops in case of circular references.
        """
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing TemplateVariableResolver")
        self.max_passes = max_passes
    
    def resolve(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute variables in configuration values.
        
        Variables can be referenced using ${variable} syntax.
        Environment variables can be referenced using ${ENV:VARIABLE} syntax.
        
        Args:
            config: Configuration dictionary to substitute variables in.
            
        Returns:
            Configuration dictionary with variables substituted.
            
        Raises:
            ValueError: If there are unresolvable variables or circular references.
        """
        self.logger.debug("Resolving variables in configuration")
        
        # Make a copy of the config to avoid modifying the original
        config_copy = copy.deepcopy(config)
        
        # Track if any substitutions were made in each pass
        substitutions_made = True
        passes = 0
        
        # Keep track of unresolved variables from the previous pass
        previous_unresolved = set()
        
        while substitutions_made and passes < self.max_passes:
            passes += 1
            substitutions_made = False
            
            # Convert the config to a string for easier substitution
            config_str = yaml.dump(config_copy)
            original_config_str = config_str
            
            # Find all variable references
            unresolved = set()
            for match in self.VAR_PATTERN.finditer(config_str):
                unresolved.add(match.group(0))
            
            # If we have the same unresolved variables as the previous pass,
            # and we've made at least one pass, we have a circular reference
            if unresolved and unresolved == previous_unresolved and passes > 1:
                self.logger.error(f"Circular reference detected: {', '.join(unresolved)}")
                raise ValueError(f"Circular reference detected: {', '.join(unresolved)}")
            
            # Update previous_unresolved for the next pass
            previous_unresolved = unresolved.copy()
            
            # Define a function to handle variable substitution
            def replace_var(match: Match) -> str:
                nonlocal substitutions_made
                
                var_name = match.group(1)
                self.logger.debug(f"Found variable reference: ${{{var_name}}}")
                
                # Handle environment variables
                if var_name.startswith("ENV:"):
                    env_var = var_name[4:]
                    self.logger.debug(f"Resolving environment variable: {env_var}")
                    if env_var in os.environ:
                        substitutions_made = True
                        return os.environ[env_var]
                    else:
                        self.logger.warning(f"Environment variable not found: {env_var}")
                        return match.group(0)  # Return the original reference
                
                # Handle config variables
                try:
                    # Split the variable name by dots to handle nested references
                    parts = var_name.split('.')
                    value = config_copy
                    
                    # Navigate through the nested structure
                    for part in parts:
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            self.logger.warning(f"Variable not found: {var_name}")
                            return match.group(0)  # Return the original reference
                    
                    # Convert the value to a string
                    if value is None:
                        str_value = ""
                    else:
                        str_value = str(value)
                    
                    substitutions_made = True
                    return str_value
                except Exception as e:
                    self.logger.error(f"Error resolving variable {var_name}: {e}")
                    return match.group(0)  # Return the original reference
            
            # Apply the substitution
            config_str = self.VAR_PATTERN.sub(replace_var, config_str)
            
            # If no substitutions were made, we're done
            if config_str == original_config_str:
                substitutions_made = False
            
            # Convert back to a dictionary
            config_copy = yaml.safe_load(config_str)
        
        # Check if we hit the maximum number of passes
        if passes >= self.max_passes and substitutions_made:
            self.logger.warning(f"Reached maximum number of passes ({self.max_passes}) when resolving variables")
            self.logger.warning("There may be circular references or unresolvable variables")
            
            # Find unresolved variables
            unresolved = []
            for match in self.VAR_PATTERN.finditer(config_str):
                unresolved.append(match.group(0))
            
            if unresolved:
                self.logger.warning(f"Unresolved variables: {', '.join(unresolved)}")
                raise ValueError(f"Unresolved variables after {self.max_passes} passes: {', '.join(unresolved)}")
        
        self.logger.debug(f"Variable resolution completed in {passes} passes")
        return config_copy 