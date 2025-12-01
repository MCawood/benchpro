# System Profiles in BenchPRO

BenchPRO uses a layered configuration system to define system-specific parameters. This allows site administrators to define defaults for a cluster (System Profile) while allowing users to override them.

## Configuration Layers

Configuration is loaded in the following order (later layers override earlier ones):

1.  **Defaults**: Hardcoded defaults in `src/benchpro/core/config.py`.
2.  **Site Config**: `/etc/benchpro/config.yaml` (Admin defined).
3.  **User Config**: `~/.config/benchpro/config.yaml` (User defined).
4.  **Project Config**: `.benchpro/config.yaml` (Project specific).
5.  **Environment Variables**: `BENCHPRO_CONFIG` pointing to a file.

## Defining a System Profile

To define a system profile for a new HPC system, create a `config.yaml` file in one of the standard paths (e.g., `/etc/benchpro/config.yaml` for site-wide, or `.benchpro/config.yaml` for a project).

### Schema

The `system` section defines the profile:

```yaml
system:
  name: <string>          # Unique name of the system (e.g., vista, stampede3)
  scheduler: <string>     # Scheduler backend: "slurm" or "local"
  default_walltime: <int> # Default walltime in seconds
  max_walltime: <int>     # Maximum allowed walltime in seconds
  max_local_tasks: <int>  # Max concurrent local tasks
  account: <string>       # Default project account for jobs
  partition: <string>     # Default partition/queue
```

### Example: Vista System Profile

For the Vista system, we defined the following profile in `.benchpro/config.yaml`:

```yaml
system:
  name: vista
  scheduler: slurm
  default_walltime: 3600
  max_walltime: 86400
  max_local_tasks: 8
  account: A-ccsc
  partition: gg
```

This configuration ensures that:
- All tasks default to using the **Slurm** scheduler.
- Jobs are submitted to the **gg** partition.
- Jobs are charged to the **A-ccsc** account.
- Walltime defaults to 1 hour (3600s).

## Usage

When you run `bp suite run`, BenchPRO loads these configurations. You can override them via CLI flags if needed (e.g., specific tasks might need a different partition).

```bash
# Uses defaults from config.yaml
bp suite run my_suite.yaml

# Overrides defaults
bp suite run my_suite.yaml --system other_system
```
