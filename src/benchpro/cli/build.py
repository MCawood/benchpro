import os
import yaml
import click
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from benchpro.core.domain import Task, ResourceRequest, TaskStatus, Build
from benchpro.core.executor import Executor
from benchpro.core.build_config import AppConfig
from benchpro.core.templating import TemplateEngine
from benchpro.core.results import ResultStore
from benchpro.core.modules import ModuleHandler
from benchpro.core.env_config import EnvConfigLoader
from benchpro.core.env_config import EnvConfigLoader
from benchpro.core.resolver import Resolver
from benchpro.core.exceptions import BuildError, ValidationError, ConfigError
from benchpro.core.config import Config
from benchpro.core.services.status_checker import StatusChecker

console = Console()

@click.group()
def app_cli():
    """Manage applications"""
    pass

from benchpro.cli.utils import get_valid_apps, get_installed_builds

@app_cli.command(name="build")
@click.argument("config_file", shell_complete=get_valid_apps)
@click.option("--dry-run", is_flag=True, help="Simulate build")
@click.option("--scheduler", help="Scheduler to use (e.g. local, slurm)")
@click.pass_context
def build_app(ctx, config_file, dry_run, scheduler):
    """Build an application from a config file"""
    try:
        # Get config
        config = ctx.obj['config']
        # Resolve config file (can be a path or profile name)
        config_path = Resolver.resolve_app(config_file)
        config_path = Resolver.resolve_app(config_file)
        if not config_path:
             raise ValidationError(f"Profile not found: {config_file}")
        
        # Verify the resolved path exists
        if not config_path.exists():
             raise ValidationError(f"Resolved profile path does not exist: {config_path}")

        # Load config
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        
        app_config = AppConfig(**config_data)
        
        # Load template - look relative to where the config file was found
        template_path = Path(app_config.build_template)
        if not template_path.is_absolute() and not template_path.exists():
            # Try relative to the resolved config file location
            template_path = config_path.parent / app_config.build_template
            
        if not template_path.exists():
            raise BuildError(f"Template not found: {app_config.build_template} (searched relative to {config_path.parent})")
            
        with open(template_path, "r") as f:
            template_content = f.read()
            
        # Resolve source path relative to config file location
        source_path = Path(app_config.source)
        is_url = app_config.source.startswith(("http://", "https://", "ftp://"))
        
        if not is_url and not source_path.is_absolute():
            # Resolve relative to config file location
            source_path = config_path.parent / app_config.source
            if not source_path.exists():
                raise BuildError(f"Source file not found: {app_config.source} (searched relative to {config_path.parent})")
        
        # Render build script
        context = app_config.model_dump()
        # Add resolved source path to context (both original and resolved)
        context["source_path"] = str(source_path)
        context["source"] = app_config.source  # Keep original for template compatibility
        
        # Initialize handlers
        module_handler = ModuleHandler()
        # Initialize handlers
        module_handler = ModuleHandler()
        from benchpro.core.config import INSTALL_ROOT
        config_dir = INSTALL_ROOT / "config"
        env_loader = EnvConfigLoader(config_dir)
        
        # Auto-infer modules from compiler and MPI
        modules_to_load = []
        if app_config.compiler and app_config.compiler.lower() not in ["system", "none"]:
            # Resolve compiler alias
            compiler_aliases = env_loader.get_aliases(app_config.compiler, "compiler")
            found_compiler = module_handler.find_available_module(compiler_aliases)
            if found_compiler:
                modules_to_load.append(found_compiler)
                # Update config to use the found name for consistency
                app_config.compiler = found_compiler
                context["compiler"] = found_compiler
                context["compiler_module"] = found_compiler
            else:
                # Fallback to original name if none found (will likely fail validation later)
                modules_to_load.append(app_config.compiler)
                context["compiler_module"] = app_config.compiler
                
        if app_config.mpi and app_config.mpi.lower() not in ["system", "none"]:
            # Resolve MPI alias
            mpi_aliases = env_loader.get_aliases(app_config.mpi, "mpi")
            found_mpi = module_handler.find_available_module(mpi_aliases)
            if found_mpi:
                modules_to_load.append(found_mpi)
                app_config.mpi = found_mpi
                context["mpi"] = found_mpi
                context["mpi_module"] = found_mpi
            else:
                modules_to_load.append(app_config.mpi)
                context["mpi_module"] = app_config.mpi
            
        # Add user-defined modules
        if app_config.modules:
            modules_to_load.extend(app_config.modules)
            
        # Validate modules
        if modules_to_load:
            # Check if modules exist (skip validation if dry-run? maybe not)
            # For now, just warn if validation fails
            # Check if modules exist
            missing_modules = module_handler.get_missing_modules(modules_to_load)
            if missing_modules:
                console.print(f"[yellow]Warning: The following requested modules were not found: {', '.join(missing_modules)}[/yellow]")
                
            # Resolve defaults
            resolved_modules = module_handler.resolve_defaults(modules_to_load)
            
            # Update config modules for consistency
            # Map resolved modules back to compiler/mpi if they match (by index or name?)
            # Since modules_to_load was built sequentially: [compiler, mpi, *modules]
            # We can map them back by index.
            
            idx = 0
            
            # Helper to extract version from module string (e.g. gcc/15.1.0 -> 15.1.0)
            def extract_version(mod_str):
                if "/" in mod_str:
                    return mod_str.split("/", 1)[1]
                return None
            
            compiler_version = None
            mpi_version = None
            
            if app_config.compiler and app_config.compiler.lower() not in ["system", "none"]:
                 # First value was compiler
                 resolved_compiler = resolved_modules[idx]
                 app_config.compiler = resolved_compiler
                 context["compiler"] = resolved_compiler
                 context["compiler_module"] = resolved_compiler
                 compiler_version = extract_version(resolved_compiler)
                 idx += 1
                 
            if app_config.mpi and app_config.mpi.lower() not in ["system", "none"]:
                 # Next value was mpi
                 resolved_mpi = resolved_modules[idx]
                 app_config.mpi = resolved_mpi
                 context["mpi"] = resolved_mpi
                 context["mpi_module"] = resolved_mpi
                 mpi_version = extract_version(resolved_mpi)
                 idx += 1
                 
            # Remaining are user modules
            if idx < len(resolved_modules):
                 app_config.modules = resolved_modules[idx:]
            
            context["modules"] = resolved_modules
            
        # Resolve environment
        env_vars = app_config.env.copy()
        
        # Compiler env
        # Pass the extracted version to resolve_env
        compiler_env = env_loader.resolve_env(app_config.compiler.split("/")[0], compiler_version, "compiler")
        if compiler_env:
            env_vars.update(compiler_env)
            
        # MPI env
        mpi_env = env_loader.resolve_env(app_config.mpi.split("/")[0], mpi_version, "mpi")
        if mpi_env:
            env_vars.update(mpi_env)
            
        context["env"] = env_vars
        
        # Check for duplicates before proceeding
        if config.apps.check_duplicates:
            store = ResultStore()
            existing_builds = store.get_builds()
            
            # Filter for duplicates
            # Match: code, version, compiler (resolved), mpi (resolved), build_label
            # active builds (COMPLETED) are the concern.
            # What about PENDING/RUNNING? Also duplicates effectively.
            
            duplicates = []
            for b in existing_builds:
                if (b.get("code") == app_config.name and
                    b.get("version") == app_config.version and
                    b.get("build_label") == app_config.build_label and
                    b.get("status") in [TaskStatus.COMPLETED, TaskStatus.PENDING, TaskStatus.RUNNING]):
                    
                    # Check compiler/mpi
                    # Internal build record uses resolved names now.
                    # app_config also updated to resolved names.
                    
                    b_compiler = b.get("compiler") or "None"
                    conf_compiler = app_config.compiler or "None"
                    
                    b_mpi = b.get("mpi") or "None"
                    conf_mpi = app_config.mpi or "None"
                    
                    if b_compiler == conf_compiler and b_mpi == conf_mpi:
                        duplicates.append(b)
            
            if duplicates:
                console.print(f"[yellow]Warning: Found {len(duplicates)} existing build(s) with identical configuration:[/yellow]")
                for d in duplicates:
                    console.print(f"  - {d['build_id']} ({d.get('status', 'unknown')})")
                    console.print(f"    Date: {d.get('build_timestamp')}")
                
                if not click.confirm("Do you want to proceed with a duplicate build?"):
                    console.print("[yellow]Build aborted.[/yellow]")
                    return
        
        # Create build task
        # Use a short UUID for the build ID (e.g. lammps-a1b2c3d4)
        from uuid import uuid4
        short_id = uuid4().hex[:8]
        task_id = f"{app_config.name}-{short_id}"
        
        # Create build workspace directory
        # Use configured root_dir for workspaces
        # Create build workspace directory
        # Use configured workspace_dir
        root_dir = Path(config.system.workspace_dir or Path.cwd() / "benchpro")
        build_dir = root_dir / "workspaces" / "apps" / task_id
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy source files to build workspace if source is a local file (not a URL)
        # URLs will be downloaded by the build script itself
        if not app_config.source.startswith(("http://", "https://", "ftp://")):
            if source_path.exists() and source_path.is_file():
                # Copy source file to build directory
                import shutil
                dest_source = build_dir / source_path.name
                shutil.copy2(source_path, dest_source)
                console.print(f"[green]Copied source file: {source_path.name}[/green]")
                # Update source in context to just the filename (since it's now in build_dir)
                context["source"] = source_path.name
        
        # Add install_prefix to context
        install_prefix = app_config.prefix or str(build_dir / "install")
        context["install_prefix"] = install_prefix

        # Now render the template with updated context (after source file is copied)
        engine = TemplateEngine(context)
        build_script = engine.render(template_content)
        
        script_path = build_dir / "build.sh"
        

        
        with open(script_path, "w") as f:
            f.write(build_script)
        os.chmod(script_path, 0o755)
        
        task = Task(
            task_id=task_id,
            suite_id="build_process",
            resources=ResourceRequest(nodes=1, threads=4, time="01:00:00"), # Default build resources
            command=f"cd {build_dir} && {script_path}",
            status=TaskStatus.PENDING,
            working_directory=str(build_dir)
        )
        
        if dry_run:
            console.print(f"[yellow]Dry run enabled. Would execute:[/yellow]")
            console.print(f"Script: {script_path}")
            console.print(build_script)
            return
            
        # Register build as PENDING immediately
        # For now, assume activation is just setting PATH to the install dir
        # Prepare activation logic and generate modules if possible
        install_dir = app_config.prefix or str(build_dir / "install")
        activation_script = f"export PATH={install_dir}/bin:$PATH"
        
        module_handler = ModuleHandler()
        
        # Check if modules are available, otherwise use PATH-based activation
        if module_handler.modules_available():
             # Only include explicitly requested runtime modules, not build-time dependencies
             runtime_modules = app_config.modules if app_config.modules else []
             
             # Create modulefiles directory
             module_dir = build_dir / "modulefiles"
             module_dir.mkdir(parents=True, exist_ok=True)
             
             # Generate module file
             try:
                 module_content = module_handler.generate_module_file(
                     name=app_config.name,
                     version=app_config.version,
                     modules=runtime_modules, 
                     paths=[f"{install_dir}/bin"],
                     env_vars=env_vars if 'env_vars' in locals() else {} # env_vars comes from earlier ctx
                 )
                 
                 module_file = module_dir / f"{app_config.name}.lua"
                 with open(module_file, "w") as f:
                     f.write(module_content)
                     
                 # Update activation script to use module
                 activation_script = f"module use {module_dir} && module load {app_config.name}"
                 console.print(f"[green]Generated module file at {module_file}[/green]")
             except Exception as e:
                 console.print(f"[yellow]Failed to generate module file: {e}. Defaulting to PATH activation.[/yellow]")
        
        else:
             console.print("[yellow]Lmod not detected. Using PATH-based activation.[/yellow]")
        
        build = Build(
            build_id=task_id,
            code=app_config.name,
            version=app_config.version,
            system=config.system.name, # Use configured system name
            build_label=app_config.build_label,
            build_timestamp=datetime.now().isoformat(),
            activation_script=activation_script,
            compiler=app_config.compiler,
            mpi=app_config.mpi,
            status=TaskStatus.PENDING
        )
        
        # We can't generate modules yet as we don't know if build will succeed
        # But we can save the build record
        store = ResultStore()
        # DELAYED REGISTRATION: User requested to save build only after successful submission.
        # store.save_build(build)
        # console.print(f"Registered build {task_id} (PENDING)")

        # Execute
        console.print(f"Starting build {task_id}...")
        
        # Determine backend
        backend = scheduler or config.system.scheduler
        console.print(f"Using scheduler: {backend}")

        # Mandatory parameter check for Slurm
        if backend == "slurm" and not config.system.account:
             console.print("[red]Mandatory parameter missing: system.account[/red]")
             val = click.prompt("Please enter your allocation/account", type=str)
             if val:
                  Config.update_user_config("system.account", val)
                  # Update current config object too
                  config.system.account = val
                  console.print(f"[green]Configuration updated with account: {val}[/green]")
             else:
                  raise click.Abort()
        
        executor = Executor(backend=backend, config=config)
        import asyncio
        from benchpro.core.domain import Benchmark
        
        bench = Benchmark(
            benchmark_id=task.task_id,
            suite_id="build_process",
            tasks=[task]
        )
        
        asyncio.run(executor.run_benchmarks([bench], suite_id="build_process"))
        
        # Check result
        if task.status in [TaskStatus.RUNNING, TaskStatus.PENDING] and backend == "slurm":
            console.print(f"[green]Build submitted successfully as Job {task.job_id}[/green]")
            # Update build with job_id
            build.job_id = task.job_id
            build.status = TaskStatus.PENDING # Still pending/running
            store.save_build(build)
            console.print(f"Registered build {task_id} (PENDING)")
            return

        if task.status == TaskStatus.COMPLETED:
            console.print(f"[green]Build successful![/green]")
            
            # Update build status
            build.status = TaskStatus.COMPLETED
            store.save_build(build)
            console.print(f"Build {task_id} completed and active")
            
        else:
            console.print(f"[red]Build failed with exit code {task.exit_code}[/red]")
            build.status = TaskStatus.FAILED
            store.save_build(build)
            
    except (ValidationError, BuildError, ConfigError):
        raise
    except Exception as e:
        raise BuildError(f"Error building app: {e}")




@app_cli.command(name="avail")
def list_available_apps():
    """List available application profiles from all search directories"""
    available = {}
    search_paths = Resolver.get_app_search_paths()
    
    for search_path in search_paths:
        profiles = []
        if search_path.exists() and search_path.is_dir():
            for profile_file in sorted(search_path.glob("*.yaml")):
                if profile_file.is_file():
                    profiles.append(profile_file)
            if profiles:
                available[str(search_path)] = profiles
    
    if not available:
        console.print("[yellow]No application profiles found in search directories[/yellow]")
        console.print("\nSearch directories:")
        search_paths = Resolver.get_profile_search_paths()
        for path in search_paths:
            console.print(f"  - {path}")
        return
    
    # Show profiles grouped by search path
    for search_path, profiles in available.items():
        console.print(f"\n[bold cyan]{search_path}[/bold cyan]")
        for profile in profiles:
            profile_name = profile.stem  # Remove .yaml extension
            console.print(f"  • {profile_name}")
    
    # Also show search paths that don't have profiles
    all_search_paths = Resolver.get_profile_search_paths()
    empty_paths = [str(p) for p in all_search_paths if str(p) not in available]
    if empty_paths:
        console.print(f"\n[yellow]Empty search directories:[/yellow]")
        for path in empty_paths:
            console.print(f"  - {path}")

@app_cli.command(name="list")
@click.option("--all", is_flag=True, help="Show all builds, not just a limited number")
@click.option("--limit", type=int, default=10, help="Limit the number of builds shown")
def list_builds(all, limit):
    """List registered builds"""
    store = ResultStore()
    builds = store.get_builds()
    
    # Lazy update of active builds
    # Sync status
    checker = StatusChecker(store)
    checker.sync_builds()
    
    # Reload builds with fresh status
    builds = store.get_builds()
    # Filter again for active/limit
    if not all:
        builds = builds[:limit]
        
    runs = builds
    
    table = Table(title="Registered Builds")
    table.add_column("Build ID", style="cyan")
    table.add_column("Code", style="green")
    table.add_column("Version", style="magenta")
    table.add_column("System")
    table.add_column("Label")
    table.add_column("Status")
    table.add_column("Timestamp")
    
    for b in builds:
        status = b.get("status", "unknown")
        status_style = "white"
        if status == TaskStatus.COMPLETED:
            status_style = "green"
        elif status == TaskStatus.FAILED:
            status_style = "red"
        elif status == TaskStatus.RUNNING:
            status_style = "yellow"
            
        table.add_row(
            b["build_id"],
            b["code"],
            b["version"],
            b["system"],
            b["build_label"],
            f"[{status_style}]{status}[/{status_style}]",
            b["build_timestamp"]
        )
    
    console.print(table)

@app_cli.command(name="info")
@click.argument("build_id", shell_complete=get_installed_builds)
def build_info(build_id):
    """Show detailed information for a specific build"""
    store = ResultStore()
    
    # Sync status first
    checker = StatusChecker(store)
    checker.sync_builds([build_id])
    
    builds = store.get_builds()
    
    # Resolve Build ID (Exact or Partial)
    matches = [b for b in builds if build_id in b["build_id"]]
    if not matches:
        console.print(f"[red]Build '{build_id}' not found[/red]")
        return
    if len(matches) > 1:
        console.print(f"[yellow]Ambiguous build ID '{build_id}'. Matches:[/yellow]")
        for m in matches:
            console.print(f"  - {m['build_id']} ({m['code']})")
        return
        
    b = matches[0]
    
    # Create Panel Content
    lines = []
    
    # Header Info
    lines.append(f"[bold cyan]Build ID:[/bold cyan] {b['build_id']}")
    lines.append(f"[bold]Code:[/bold] {b['code']} @ {b['version']}")
    lines.append(f"[bold]Timestamp:[/bold] {b['build_timestamp']}")
    
    # Status coloring
    status = b.get("status", "UNKNOWN")
    color = "white"
    if status == "completed": color = "green"
    elif status == "failed": color = "red" 
    elif status == "running": color = "yellow"
    lines.append(f"[bold]Status:[/bold] [{color}]{status.upper()}[/{color}]")
    
    lines.append("")
    lines.append("[bold underline]Configuration[/bold underline]")
    lines.append(f"  [bold]System:[/bold] {b.get('system', 'unknown')}")
    lines.append(f"  [bold]Compiler:[/bold] {b.get('compiler', 'None')}")
    lines.append(f"  [bold]MPI:[/bold] {b.get('mpi', 'None')}")
    lines.append(f"  [bold]Label:[/bold] {b.get('build_label', 'default')}")
    
    lines.append("")
    lines.append("[bold underline]Scheduler Details[/bold underline]")
    lines.append(f"  [bold]Job ID:[/bold] {b.get('job_id', 'N/A')}")
    
    lines.append("")
    lines.append("[bold underline]Paths & Files[/bold underline]")
    
    # Extract paths from activation script or reconstruct
    # We can infer workspace from config if needed, or rely on what we know
    # Since we don't store absolute paths in Build model except activation_script...
    # activation_script="module use /path/to/workspace && ..."
    
    # Try to parse workspace from activation script
    workspace = "Unknown"
    activation_script = b.get("activation_script", "")
    
    if "module use" in activation_script:
        try:
            parts = activation_script.split("module use ")[1].split(" &&")[0]
            ws_path = Path(parts.strip())
            # If path ends in 'modulefiles', parent is the workspace root
            if ws_path.name == "modulefiles":
                workspace = str(ws_path.parent)
            else:
                workspace = str(ws_path)
        except:
            pass
    elif "export PATH=" in activation_script:
         # export PATH=/path/to/install/bin:$PATH
         try:
             path_val = activation_script.split("PATH=")[1].split(":")[0]
             # This is install/bin. Workspace is likely 2 levels up if standard.
             install_bin = Path(path_val)
             workspace = str(install_bin.parent.parent) 
         except:
             pass

    # Helper for existence check
    def checked_path(path_str):
        if not path_str or path_str == "Unknown":
            return "[dim]Unknown[/dim]"
        p = Path(path_str)
        if p.exists():
            return f"[green]{path_str}[/green]"
        return f"[red]{path_str} (missing)[/red]"

    lines.append(f"  [bold]Workspace:[/bold] {checked_path(workspace)}")
    
    # Log files?
    # They are typically in workspace/build.log or similar?
    # Current executor stores task logs in workspace/{task_id}.out
    # task_id == build_id
    if workspace != "Unknown":
        out_log = Path(workspace) / f"{b['build_id']}.out"
        err_log = Path(workspace) / f"{b['build_id']}.err"
        lines.append(f"  [bold]Stdout:[/bold] {checked_path(str(out_log))}")
        lines.append(f"  [bold]Stderr:[/bold] {checked_path(str(err_log))}")
        
        # Module file
        # Check standard location in root or modulefiles subdir
        module_file = Path(workspace) / f"{b['code']}.lua"
        if not module_file.exists():
             module_file = Path(workspace) / "modulefiles" / f"{b['code']}.lua"
             
        lines.append(f"  [bold]Module:[/bold] {checked_path(str(module_file))}")
        
        # Binary check (heuristic)
        # Try finding a binary in install/bin that matches the code name
        # Common pattern: lammps -> lmp, or just lammps -> lammps
        # Let's try standard locations
        install_bin = Path(workspace) / "install" / "bin"
        if install_bin.exists():
             # Check for exact match first
             candidates = [b['code']]
             # Add common aliases? No, kept simple for now or check both
             if b['code'] == 'lammps': candidates.append("lmp")
             
             found_binary = None
             for cand in candidates:
                 p = install_bin / cand
                 if p.exists():
                     found_binary = p
                     break
             
             if found_binary:
                 lines.append(f"  [bold]Binary:[/bold] [green]{found_binary}[/green]")
             else:
                 lines.append(f"  [bold]Binary:[/bold] [dim]Not found in standard location[/dim]")
        
    console.print(Panel("\n".join(lines), title=f"Application Build: {b['code']}", expand=False))

@app_cli.command(name="delete")
@click.argument("build_id", required=False, shell_complete=get_installed_builds)
@click.option("--code", help="Delete all builds for a given code")
@click.option("--all", is_flag=True, help="Delete all builds")
@click.confirmation_option(prompt="Are you sure you want to delete these builds?")
def delete_build(build_id, code, all):
    """Delete registered builds"""
    store = ResultStore()
    from benchpro.core.scheduler import SlurmBackend
    scheduler = SlurmBackend()
    
    builds_to_delete = []
    
    if all:
        builds_to_delete = store.get_builds()
    elif code:
        # We need to query builds by code manually since store doesn't return objects for get_builds?
        # store.get_builds() returns list of dicts.
        all_builds = store.get_builds()
        builds_to_delete = [b for b in all_builds if b["code"] == code]
    elif build_id:
        # Find specific build
        all_builds = store.get_builds()
        match = next((b for b in all_builds if b["build_id"] == build_id), None)
        if match:
            builds_to_delete = [match]
    
    if not builds_to_delete:
        if build_id:
             console.print(f"[red]Build {build_id} not found[/red]")
        elif code:
             console.print(f"[yellow]No builds found for code '{code}'[/yellow]")
        else:
             console.print("[yellow]No builds found[/yellow]")
        return

    # Cancel active jobs
    jobs_to_wait = []
    
    for b in builds_to_delete:
        status = b.get("status")
        job_id = b.get("job_id")
        
        if status in [TaskStatus.PENDING, TaskStatus.RUNNING] and job_id:
            try:
                console.print(f"Cancelling job {job_id} for build {b['build_id']}...")
                if scheduler.cancel_job(str(job_id)):
                    console.print(f"[green]Cancelled job {job_id}[/green]")
                    jobs_to_wait.append(str(job_id))
                else:
                    console.print(f"[yellow]Failed to cancel job {job_id} (might have already finished)[/yellow]")
            except Exception as e:
                console.print(f"[red]Error cancelling job {job_id}: {e}[/red]")
    
    if jobs_to_wait:
         with console.status(f"[bold blue]Waiting for {len(jobs_to_wait)} job(s) to terminate...[/bold blue]"):
             if scheduler.wait_for_jobs(jobs_to_wait):
                 console.print("[green]All jobs terminated[/green]")
             else:
                 console.print("[yellow]Timeout waiting for jobs to terminate. Proceeding with deletion anyway.[/yellow]")
    deleted_count = 0
    
    # helper to find workspace
    def get_workspace(b):
        # Try from activation script
        script = b.get("activation_script", "")
        if "module use" in script:
            try:
                parts = script.split("module use ")[1].split(" &&")[0]
                p = Path(parts.strip())
                if p.name == "modulefiles":
                    return p.parent
                return p
            except:
                pass
        elif "export PATH=" in script:
            try:
                path_val = script.split("PATH=")[1].split(":")[0]
                return Path(path_val).parent.parent
            except:
                pass
        return None

    config = Config.load()
    root_dir = Path(config.system.workspace_dir or Path.cwd() / "benchpro")
    
    import shutil
    
    for b in builds_to_delete:
        bid = b["build_id"]
        
        # 1. Delete workspace
        ws = get_workspace(b)
        
        # Fallback to standard paths if parsing failed
        possible_paths = []
        if ws:
             possible_paths.append(ws)
        
        # Check standard new path
        possible_paths.append(root_dir / "workspaces" / "apps" / bid)
        # Check legacy path
        possible_paths.append(root_dir / "workspaces" / bid)
        
        workspace_deleted = False
        for p in possible_paths:
             if p.exists() and p.is_dir():
                 if "workspaces" not in str(p):
                     # Safety check: ensure we are not deleting something outside workspaces unless verified?
                     # Workspace path should definitely contain "workspaces" if standard.
                     # But custom root?
                     # Let's trust it if it matches build_id at end
                     if not str(p).endswith(bid):
                          console.print(f"[yellow]Skipping unsafe path: {p}[/yellow]")
                          continue
                          
                 try:
                     shutil.rmtree(p)
                     console.print(f"Deleted workspace: {p}")
                     workspace_deleted = True
                     break # Stop after finding one? Or check others? 
                     # Usually only one exists.
                 except Exception as e:
                     console.print(f"[red]Failed to delete workspace {p}: {e}[/red]")

        # 2. Delete record
        if store.delete_build(bid):
            deleted_count += 1
            
    console.print(f"[green]Deleted {deleted_count} build(s)[/green]")
@app_cli.command(name="purge")
@click.option("--force", is_flag=True, help="Force purge without confirmation")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def purge_apps(force, yes):
    """Purge all application builds and data"""
    if not (force or yes):
        click.confirm("Are you sure you want to purge ALL application builds and data? This cannot be undone.", abort=True)
        
    store = ResultStore()
    config = Config.load()
    
    # 0. Cancel all active jobs
    from benchpro.core.scheduler import SlurmBackend
    scheduler = SlurmBackend()
    
    builds = store.get_builds()
    for b in builds:
        status = b.get("status")
        job_id = b.get("job_id")
        if status in [TaskStatus.PENDING, TaskStatus.RUNNING] and job_id:
            try:
                if scheduler.cancel_job(str(job_id)):
                    console.print(f"[green]Cancelled job {job_id}[/green]")
            except Exception:
                pass # Ignore errors during mass purge
    
    # 1. Clear database
    count = store.clear_all_builds()
    console.print(f"[green]Cleared {count} build records from database[/green]")
    
    # 2. Clear workspaces
    root_dir = Path(config.system.workspace_dir or Path.cwd() / "benchpro")
    workspaces_dir = root_dir / "workspaces"
    apps_dir = workspaces_dir / "apps"
    
    deleted_dirs = 0
    
    # Strategy:
    # We now isolate apps in workspaces/apps, so we can safely delete that entire directory
    # or iterate its contents.
    
    if apps_dir.exists():
        import shutil
        for item in apps_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                    deleted_dirs += 1
                else:
                    item.unlink()
            except Exception as e:
                pass
                
        console.print(f"[green]Deleted {deleted_dirs} application workspaces from {apps_dir}[/green]")
    else:
        # Check for legacy build workspaces in root?
        # Only if they start with build_?
        # Let's clean them up too if we are purging ALL apps.
        if workspaces_dir.exists():
             legacy_count = 0
             for item in workspaces_dir.iterdir():
                 if item.is_dir() and item.name.startswith("build_"):
                     try:
                         shutil.rmtree(item)
                         legacy_count += 1
                     except Exception:
                         pass
             if legacy_count:
                 console.print(f"[green]Deleted {legacy_count} legacy build workspaces[/green]")
                 deleted_dirs += legacy_count
        
        if deleted_dirs == 0:
            console.print("[yellow]No application workspaces found to purge[/yellow]")
        
        # Also delete install directory?

