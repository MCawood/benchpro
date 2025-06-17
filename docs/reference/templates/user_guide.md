# Working with Templates

This guide provides practical examples and best practices for creating and customizing templates in BenchPRO.

## Creating Task Templates

The block-based template system allows you to create concise, focused templates that contain only the task-specific commands. The system will automatically add common elements like headers, environment setup, and logging.

### Application Build Templates

A typical application build template might look like this:

```jinja
# Build the application
echo "Building {{ name }} version {{ version }}"

# Create build directory if it doesn't exist
mkdir -p {{ workspace.build_dir }}

# Configure build parameters
{% if build.compiler %}
COMPILER={{ build.compiler }}
{% else %}
COMPILER=gcc
{% endif %}

{% if build.flags %}
FLAGS="{{ build.flags }}"
{% else %}
FLAGS="-O2"
{% endif %}

# Execute the build
cd {{ workspace.source_dir }}
$COMPILER $FLAGS -o {{ workspace.build_dir }}/{{ build.output }} {{ build.source }}

# Test the build
if [ -f "{{ workspace.build_dir }}/{{ build.output }}" ]; then
    echo "Build successful!"
    exit 0
else
    echo "Build failed!"
    exit 1
fi
```

### Benchmark Run Templates

A benchmark template might look like this:

```jinja
# Run the benchmark
echo "Running {{ name }} version {{ version }}"

# Set up input/output directories
mkdir -p {{ workspace.results_dir }}

# Configure runtime parameters
{% if run.threads %}
export OMP_NUM_THREADS={{ run.threads }}
{% endif %}

# Execute the benchmark
{{ run.application_path }} {{ run.arguments }} > {{ workspace.results_dir }}/output.log 2>&1

# Check for successful execution
if [ $? -eq 0 ]; then
    echo "Benchmark completed successfully!"
    exit 0
else
    echo "Benchmark failed with exit code $?"
    exit 1
fi
```

## Variable Reference

The following variables are available in templates:

### Common Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `name` | Task name | `"hello_world"` |
| `version` | Task version | `"1.0"` |
| `task_type` | Type of task | `"application"` or `"benchmark"` |
| `execution_context` | Execution context | `"local"` or `"slurm"` |

### Workspace Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `workspace.workspace_dir` | Root workspace directory | `"/path/to/workspace"` |
| `workspace.source_dir` | Source code directory | `"/path/to/workspace/source"` |
| `workspace.build_dir` | Build output directory | `"/path/to/workspace/build"` |
| `workspace.logs_dir` | Log file directory | `"/path/to/workspace/logs"` |
| `workspace.results_dir` | Results output directory | `"/path/to/workspace/results"` |

### Job Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `job.name` | Job name | `"hello_world_job"` |
| `job.queue` | Job queue/partition | `"standard"` |
| `job.nodes` | Number of nodes | `1` |
| `job.tasks_per_node` | Tasks per node | `4` |
| `job.time_limit` | Job time limit | `"01:00:00"` |
| `job.account` | Job accounting code | `"project123"` |

### Build Variables (Applications)

| Variable | Description | Example |
|----------|-------------|---------|
| `build.source` | Source file(s) | `"hello_world.c"` |
| `build.compiler` | Compiler | `"gcc"` |
| `build.flags` | Compiler flags | `"-O3 -march=native"` |
| `build.output` | Output binary name | `"hello_world"` |
| `build.threads` | Build threads | `4` |

### Run Variables (Benchmarks)

| Variable | Description | Example |
|----------|-------------|---------|
| `run.application` | Application name | `"hello_world"` |
| `run.application_path` | Path to application binary | `"/path/to/hello_world"` |
| `run.arguments` | Command-line arguments | `"-n 1000 -v"` |
| `run.threads` | Execution threads | `4` |
| `run.input_files` | Input files | `["input.dat", "params.cfg"]` |
| `run.output_files` | Output files to capture | `["output.log", "results.csv"]` |

## Using Jinja2 Features

Templates use Jinja2 syntax, which provides powerful features for creating flexible templates:

### Conditionals

```jinja
{% if build.threads %}
export OMP_NUM_THREADS={{ build.threads }}
{% else %}
export OMP_NUM_THREADS=1
{% endif %}
```

### Loops

```jinja
{% for file in run.input_files %}
cp {{ workspace.input_dir }}/{{ file }} .
{% endfor %}
```

### Variables and Expressions

```jinja
export THREADS={{ run.threads if run.threads else 1 }}
```

### Filters

```jinja
echo "Running {{ name | upper }} version {{ version }}"
```

## Best Practices

1. **Focus on Task-Specific Commands**
   - Don't include standard elements like shebang lines, timestamp logging, etc.
   - The template system will add these automatically.

2. **Use Error Handling**
   - Check for failures and exit with appropriate codes.
   - Capture important output to log files.

3. **Leverage Conditionals**
   - Make templates adaptable to different configurations.
   - Provide sensible defaults when variables are missing.

4. **Keep Templates Readable**
   - Use comments to explain what the template is doing.
   - Group related commands together.

5. **Validate Paths**
   - Check for the existence of directories and files.
   - Create directories if needed.

## Customizing the Template System

For advanced users who need to customize how the template system works:

1. **Custom Blocks**: Add special-purpose blocks for specific needs.
2. **Priority Adjustment**: Change block ordering for special requirements.
3. **Context-Specific Blocks**: Create blocks that only apply to specific execution contexts.

See the [Advanced Template Customization](advanced.md) guide for more details on these topics. 