# BenchPRO 2.0 Installation Guide

This guide is intended for site maintainers deploying BenchPRO 2.0 on an HPC system.

## Prerequisites
- Python 3.9+
- Lmod (for module generation)
- Git

## Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/TACC/benchpro-ng.git
   cd benchpro-ng
   ```

2. **Run the Installation Script**
   The `install.sh` script installs BenchPRO into a self-contained virtual environment and generates an Lmod module file.
   
   Usage: `./scripts/install.sh [INSTALL_PREFIX]`
   
   Example (installing to `/opt/apps`):
   ```bash
   ./scripts/install.sh /opt/apps
   ```
   
   This will create:
   - `/opt/apps/benchpro/<version>/venv`: Virtual environment
   - `/opt/apps/benchpro/<version>/bin`: Executables
   - `/opt/apps/benchpro/<version>/config`: Site configuration
   - `/opt/apps/benchpro/<version>/modulefiles`: Lmod module file

3. **Deploy the Module File**
   Copy the generated module file to your system's module path.
   ```bash
   cp /opt/apps/benchpro/<version>/modulefiles/<version>.lua /opt/modulefiles/benchpro/
   ```

4. **Configure Site Defaults**
   Edit `/opt/apps/benchpro/<version>/config/benchpro.yaml` to set site-wide defaults (e.g., scheduler, account, partition).
   ```yaml
   system:
     name: "stampede3"
     scheduler: "slurm"
     account: "MyAccount"
     partition: "normal"
   ```

5. **Install Site Profiles**
   Place shared task profiles in `/opt/apps/benchpro/<version>/config/profiles`.

## User Setup
Users do not need to run any manual setup commands. On the first run of `bp`, BenchPRO will automatically:
1. Detect that `~/.config/benchpro` is missing.
2. Initialize the user configuration directory.
3. Create a default `config.yaml`.

## Verification
To verify the installation:
```bash
module load benchpro
bp --version
bp config show
```
