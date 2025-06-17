## Benchmark Configuration

### Requirements Section

The `requirements` section allows you to specify application dependencies for your benchmark. BenchPRO will automatically:

1. Search for matching applications in the registry
2. Add the application's environment modules to your benchmark
3. Configure appropriate module paths

Here's how to use the requirements section:

```yaml
requirements:
  # Required field - the name of the application to use
  application: "my_application" 
  # Optional - specific version to use
  version: "1.0"  
  # Optional - specific label to match (e.g., "mpi", "cuda")
  label: "mpi"
```

When you specify requirements:
- BenchPRO searches for applications matching these criteria
- If multiple matching applications exist, the most recently built is selected
- The application's module file and environment settings are merged with your benchmark configuration
- You can access application information in templates via `dependencies.application`

#### Example Template with Requirements

```jinja
#!/bin/bash

# Print application information
{% if dependencies.application %}
echo "Using application: {{ dependencies.application.name }} v{{ dependencies.application.version }}"
{% endif %}

# Run the executable
{{ run.executable }} {{ run.arguments }}
```

### Run Section 