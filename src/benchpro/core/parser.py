import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from benchpro.core.domain import MetricDefinition

class ResultParser:
    @staticmethod
    def parse(file_path: Path, metrics: List[MetricDefinition]) -> Dict[str, Any]:
        """
        Parse a file and extract metrics based on definitions.
        """
        if not file_path.exists():
            return {}
            
        content = file_path.read_text()
        results = {}
        
        for metric in metrics:
            try:
                match = re.search(metric.regex, content)
                if match:
                    # If groups are present, take the first group
                    if match.groups():
                        value = match.group(1)
                    else:
                        value = match.group(0)
                        
                    # Try to convert to float/int
                    try:
                        if "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass # Keep as string
                        
                    results[metric.name] = {
                        "value": value,
                        "unit": metric.unit
                    }
            except re.error as e:
                print(f"Error parsing metric {metric.name}: {e}")
                
        return results
