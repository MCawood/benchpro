import subprocess
import shutil
from pathlib import Path
from typing import List, Optional
from benchpro.core.logger import get_logger

logger = get_logger()

class ModuleHandler:
    def __init__(self):
        self.lmod_cmd = shutil.which("module") or "module"
    
    def modules_available(self) -> bool:
        """
        Check if Lmod modules are available on this system.
        Returns True if 'module' command works, False otherwise.
        """
        try:
            # Try to run a simple module command
            result = subprocess.run(
                ["bash", "-l", "-c", "module --version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Module system check failed: {e}")
            return False

    def validate_modules(self, modules: List[str]) -> bool:
        """Check if modules exist using 'module avail'."""
        if not modules:
            return True
            
        # This is a basic check. 'module avail' output is hard to parse reliably 
        # for exact matches without -t, but -t lists everything.
        # A better approach for validation might be trying to load them in a subshell.
        cmd = f"module load {' '.join(modules)} && echo 'SUCCESS'"
        try:
            # Run in a shell that supports modules (bash -l)
            result = subprocess.run(
                ["bash", "-l", "-c", cmd], 
                capture_output=True, 
                text=True
            )
            return "SUCCESS" in result.stdout
        except subprocess.SubprocessError as e:
            logger.debug(f"Failed to validate modules {modules}: {e}")
            return False

    def get_missing_modules(self, modules: List[str]) -> List[str]:
        """Return list of modules that fail to load."""
        missing = []
        for mod in modules:
            if not self.validate_modules([mod]):
                missing.append(mod)
        return missing

    def find_available_module(self, candidates: List[str]) -> Optional[str]:
        """
        Find the first module from the list of candidates that exists on the system.
        Returns the name of the found module, or None if none exist.
        """
        for candidate in candidates:
            # Use validate_modules logic but for a single module
            # We use 'module avail' check which is safer than load for discovery
            # But validate_modules uses load... let's use a lighter check here
            # 'module -t avail candidate'
            try:
                cmd = ["bash", "-l", "-c", f"module -t avail {candidate}"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Check if output contains the module name
                # Lmod output is tricky. If we search for 'gnu', it might show 'gnu/9.3.0'
                # If we get any output that looks like a module, it's a match.
                output = result.stderr.strip() + "\n" + result.stdout.strip()
                if candidate in output or (output and not "No module" in output):
                    return candidate
            except subprocess.SubprocessError as e:
                logger.debug(f"Failed to check module availability for {candidate}: {e}")
                continue
                
        return None

    def resolve_defaults(self, modules: List[str]) -> List[str]:
        """
        Resolve default versions for modules without version specifiers.
        Uses 'module -t -d av <name>' to find the default.
        """
        resolved = []
        for mod in modules:
            if "/" in mod:
                resolved.append(mod)
                continue
                
            # Query Lmod for default
            try:
                # -t: terse, -d: default only, av: avail
                cmd = ["bash", "-l", "-c", f"module -t -d av {mod}"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Output format is usually path/to/module: name/version
                # Or just name/version if terse
                # Lmod writes to stderr, but shell errors might also be there
                
                # Combine stdout and stderr
                output = result.stderr.strip() + "\n" + result.stdout.strip()
                
                if output:
                    lines = output.splitlines()
                    found = False
                    for line in lines:
                        line = line.strip()
                        # Ignore shell errors or empty lines
                        if "bad substitution" in line or not line:
                            continue
                        if line.endswith(":"):
                            continue
                            
                        # Valid module usually has a slash and no spaces (mostly)
                        if "/" in line and " " not in line:
                            resolved.append(line)
                            found = True
                            break
                    
                    if not found:
                        resolved.append(mod)
                else:
                    resolved.append(mod)
            except subprocess.SubprocessError as e:
                logger.warning(f"Failed to resolve default for {mod}: {e}")
                resolved.append(mod)
                
        return resolved

    def generate_module_file(self, name: str, version: str, modules: List[str], paths: List[str], env_vars: dict) -> str:
        """Generate Lua module file content."""
        lines = [
            f'-- Module file for {name}/{version}',
            'help([[',
            f'    This module loads the environment for {name} version {version}',
            '    Built by BenchPRO',
            ']])',
            '',
            'whatis("Name: " .. myModuleName())',
            f'whatis("Version: {version}")',
            ''
        ]
        
        # Only add dependencies section if there are modules to load
        if modules:
            lines.append('-- Dependencies')
            for mod in modules:
                # Use try_load to gracefully handle missing modules
                lines.append(f'try_load("{mod}")')
            lines.append('')
            
        lines.append('')
        lines.append('-- Paths')
        for path in paths:
            lines.append(f'prepend_path("PATH", "{path}")')
            
        lines.append('')
        lines.append('-- Environment Variables')
        for key, val in env_vars.items():
            lines.append(f'setenv("{key}", "{val}")')
            
        return "\n".join(lines)
