# BenchPRO User Guide

## Overview

BenchPRO is an intelligent benchmarking platform for Linux HPC systems that automates the process of running and analyzing performance benchmarks.

## Installation

### System Requirements
- Python 3.12 or later
- Linux-based operating system
- Access to HPC resources (optional)

### TACC Systems

BenchPRO is pre-installed on most TACC systems:

| System    | Module Path                              |
|-----------|------------------------------------------|
| Frontera  | /scratch1/hpc_tools/benchpro/modulefiles |
| Stampede2 | /scratch/hpc_tools/benchpro/modulefiles  |
| Lonestar6 | /scratch/projects/benchpro/modulefiles   |

To use BenchPRO on TACC systems:

1. Load the module:
```bash
ml python3
ml use [module_path]
ml benchpro
```

2. Initialize workspace:
```bash
benchpro --validate
```

3. View system information:
```bash
benchpro --notices
benchpro --defaults
```

### Manual Installation

1. Install using pip:
```bash
pip install benchpro
```

2. Or install from source:
```bash
git clone https://github.com/yourusername/benchpro.git
cd benchpro
pip install -e .
```

## Basic Usage

### Creating Tasks

1. Create a new task:
```bash
benchpro task create --name mytask --template hello_world.sh
```

2. Set task variables:
```bash
benchpro task set mytask cores=4 memory=8G
```

3. View task status:
```bash
benchpro task status mytask
```

### Running Tasks

1. Submit a task:
```bash
benchpro task run mytask
```

2. Monitor progress:
```bash
benchpro task monitor mytask
```

3. View results:
```bash
benchpro task results mytask
```

### Managing Tasks

1. List all tasks:
```bash
benchpro task list
```

2. Stop a running task:
```bash
benchpro task stop mytask
```

3. Clean up task resources:
```bash
benchpro task clean mytask
```

## Templates

### Basic Template Structure
```bash
#!/bin/bash
#SBATCH --job-name={name}
#SBATCH --nodes={nodes}
#SBATCH --ntasks-per-node={tasks_per_node}
#SBATCH --time={walltime}

module load {modules}

srun {executable} {arguments}
```

### Template Variables
- `name`: Task name
- `nodes`: Number of nodes
- `tasks_per_node`: Tasks per node
- `walltime`: Maximum runtime
- `modules`: Required modules
- `executable`: Program to run
- `arguments`: Command line arguments

### Creating Templates

1. Create a new template:
```bash
benchpro template create mytemplate
```

2. Edit template:
```bash
benchpro template edit mytemplate
```

3. Validate template:
```bash
benchpro template validate mytemplate
```

## Resource Management

### Specifying Resources

1. CPU cores:
```bash
benchpro task set mytask cores=4
```

2. Memory:
```bash
benchpro task set mytask memory=8G
```

3. GPUs:
```bash
benchpro task set mytask gpus=1
```

### Resource Monitoring

1. View current usage:
```bash
benchpro task resources mytask
```

2. Monitor in real-time:
```bash
benchpro task monitor mytask --resources
```

3. Get resource history:
```bash
benchpro task history mytask
```

## Configuration

### System Configuration
```yaml
# config.yaml
executor:
  type: local  # or slurm
  max_tasks: 10
  default_resources:
    cores: 1
    memory: 1G

templates:
  path: /path/to/templates
  default: hello_world.sh

logging:
  level: INFO
  file: benchpro.log
```

### User Configuration
```yaml
# user_config.yaml
default_resources:
  cores: 4
  memory: 8G
  walltime: 1:00:00

templates:
  favorites:
    - hello_world.sh
    - benchmark.sh
```

## Troubleshooting

### Common Issues

1. Task fails to start:
- Check resource availability
- Verify template syntax
- Ensure paths are correct

2. Resource allocation fails:
- Check system limits
- Verify resource requests
- Check for conflicts

3. Template errors:
- Validate template syntax
- Check variable definitions
- Verify file permissions

### Getting Help

1. View command help:
```bash
benchpro --help
benchpro task --help
```

2. Check logs:
```bash
benchpro logs show
```

3. Contact support:
```bash
benchpro support request
```

## Best Practices

1. **Resource Requests**
- Request slightly more than needed
- Consider memory overhead
- Account for startup time

2. **Templates**
- Use variables for flexibility
- Include error handling
- Document requirements

3. **Task Management**
- Use descriptive names
- Monitor resource usage
- Clean up after completion

4. **Performance**
- Start with small tests
- Increment resources gradually
- Document optimal settings 