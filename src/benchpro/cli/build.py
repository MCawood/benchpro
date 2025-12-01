import os
import yaml
import click
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table

from benchpro.core.domain import Task, ResourceRequest, TaskStatus, Build
from benchpro.core.executor import Executor
from benchpro.core.build_config import AppConfig
from benchpro.core.templating import TemplateEngine
from benchpro.core.results import ResultStore
from benchpro.core.modules import ModuleHandler
from benchpro.core.env_config import EnvConfigLoader
from benchpro.core.resolver import Resolver

console = Console()

@click.group()
def app_cli():
    """Manage applications"""
    pass

@app_cli.command(name="build")
@click.argument("config_file")
@click.option("--dry-run", is_flag=True, help="Simulate build")
@click.pass_context
def build_app(ctx, config_file, dry_run):
    """Build an application from a config file"""
    try:
        # Get config
        config = ctx.obj['config']
        # Resolve config file (can be a path or profile name)
        config_path = Resolver.resolve_app(config_file)
        if not config_path:
             raise FileNotFoundError(f"Profile not found: {config_file}")
        
        # Verify the resolved path exists
        if not config_path.exists():
             raise FileNotFoundError(f"Resolved profile path does not exist: {config_path}")

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
            raise FileNotFoundError(f"Template not found: {app_config.build_template} (searched relative to {config_path.parent})")
            
        with open(template_path, "r") as f:
            template_content = f.read()
            
        # Resolve source path relative to config file location
        source_path = Path(app_config.source)
        if not source_path.is_absolute():
            # Resolve relative to config file location
            source_path = config_path.parent / app_config.source
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {app_config.source} (searched relative to {config_path.parent})")
        
        # Render build script
        context = app_config.model_dump()
        # Add resolved source path to context (both original and resolved)
        context["source_path"] = str(source_path)
        context["source"] = app_config.source  # Keep original for template compatibility
        
        # Initialize handlers
        module_handler = ModuleHandler()
        config_dir = Path(__file__).parent.parent / "config"
        env_loader = EnvConfigLoader(config_dir)
        
        # Auto-infer modules from compiler and MPI
        modules_to_load = []
        if app_config.compiler and app_config.compiler.lower() not in ["system", "none"]:
            modules_to_load.append(app_config.compiler)
        if app_config.mpi and app_config.mpi.lower() not in ["system", "none"]:
            modules_to_load.append(app_config.mpi)
            
        # Add user-defined modules
        if app_config.modules:
            modules_to_load.extend(app_config.modules)
            
        # Validate modules
        if modules_to_load:
            # Check if modules exist (skip validation if dry-run? maybe not)
            # For now, just warn if validation fails
            if not module_handler.validate_modules(modules_to_load):
                console.print("[yellow]Warning: Some requested modules may not exist[/yellow]")
                
            # Resolve defaults
            resolved_modules = module_handler.resolve_defaults(modules_to_load)
            # Update config modules for consistency, though we use resolved_modules for generation
            app_config.modules = resolved_modules 
            context["modules"] = resolved_modules
            
        # Resolve environment
        env_vars = app_config.env.copy()
        
        # Compiler env
        compiler_env = env_loader.resolve_env(app_config.compiler, None, "compiler")
        if compiler_env:
            env_vars.update(compiler_env)
            
        # MPI env
        mpi_env = env_loader.resolve_env(app_config.mpi, None, "mpi")
        if mpi_env:
            env_vars.update(mpi_env)
            
        context["env"] = env_vars
        
        # Create build task
        task_id = f"build_{app_config.name}_{app_config.version}_{int(datetime.now().timestamp())}"
        
        # Create build workspace directory
        # Use configured root_dir for workspaces
        root_dir = Path(config.defaults.get("root_dir", Path.cwd() / "benchpro"))
        build_dir = root_dir / "workspaces" / task_id
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
            resources=ResourceRequest(nodes=1, threads=4), # Default build resources
            command=f"cd {build_dir} && {script_path}",
            status=TaskStatus.PENDING
        )
        
        if dry_run:
            console.print(f"[yellow]Dry run enabled. Would execute:[/yellow]")
            console.print(f"Script: {script_path}")
            console.print(build_script)
            return

        # Execute
        console.print(f"Starting build {task_id}...")
        executor = Executor(backend="local") # Builds usually run locally or on login nodes for now
        import asyncio
        asyncio.run(executor.run_tasks([task], suite_id="build_process"))
        
        # Check result
        if task.status == TaskStatus.COMPLETED:
            console.print(f"[green]Build successful![/green]")
            
            # Register build
            # For now, assume activation is just setting PATH to the install dir
            # In reality, the build script should produce an activation script or module
            install_dir = app_config.prefix or str(build_dir / "install")
            activation_script = f"export PATH={install_dir}/bin:$PATH"
            
            build = Build(
                build_id=task_id,
                code=app_config.name,
                version=app_config.version,
                system="local", # TODO: Get from system config
                build_label=app_config.build_label,
                build_timestamp=datetime.now().isoformat(),
                activation_script=activation_script,
                compiler=app_config.compiler,
                mpi=app_config.mpi
            )
            
            # Check if modules are available, otherwise use PATH-based activation
            if module_handler.modules_available():
                # Only include explicitly requested runtime modules, not build-time dependencies
                # Build-time modules (compiler, MPI) are only needed during build, not runtime
                runtime_modules = app_config.modules if app_config.modules else []
                
                # Generate module file (only with runtime modules, not build-time deps)
                module_content = module_handler.generate_module_file(
                    name=app_config.name,
                    version=app_config.version,
                    modules=runtime_modules,  # Only explicitly requested modules
                    paths=[f"{install_dir}/bin"],
                    env_vars=env_vars
                )
                
                module_file = build_dir / f"{app_config.name}.lua"
                with open(module_file, "w") as f:
                    f.write(module_content)
                    
                # Update activation script to use module
                # We use 'module use' to add the build dir to module path
                build.activation_script = f"module use {build_dir} && module load {app_config.name}"
            else:
                # Fall back to PATH-based activation (for systems without Lmod)
                console.print("[yellow]Modules not available, using PATH-based activation[/yellow]")
                # activation_script already set to PATH-based above
            
            store = ResultStore()
            store.save_build(build)
            console.print(f"Registered build {task_id}")
            
        else:
            console.print(f"[red]Build failed with exit code {task.exit_code}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error building app: {e}[/red]")
        # import traceback
        # traceback.print_exc()

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
def list_builds():
    """List registered builds"""
    store = ResultStore()
    builds = store.get_builds()
    
    table = Table(title="Registered Builds")
    table.add_column("Build ID", style="cyan")
    table.add_column("Code", style="green")
    table.add_column("Version", style="magenta")
    table.add_column("System")
    table.add_column("Label")
    table.add_column("Timestamp")
    
    for b in builds:
        table.add_row(
            b["build_id"],
            b["code"],
            b["version"],
            b["system"],
            b["build_label"],
            b["build_timestamp"]
        )
    
    console.print(table)

@app_cli.command(name="delete")
@click.argument("build_id", required=False)
@click.option("--code", help="Delete all builds for a given code")
@click.option("--all", is_flag=True, help="Delete all builds")
@click.confirmation_option(prompt="Are you sure you want to delete these builds?")
def delete_build(build_id, code, all):
    """Delete registered builds"""
    store = ResultStore()
    
    if all:
        builds = store.get_builds()
        deleted_count = 0
        for b in builds:
            if store.delete_build(b["build_id"]):
                deleted_count += 1
        console.print(f"[green]Deleted {deleted_count} build(s)[/green]")
    elif code:
        deleted_count = store.delete_builds_by_code(code)
        console.print(f"[green]Deleted {deleted_count} build(s) for code '{code}'[/green]")
    elif build_id:
        if store.delete_build(build_id):
            console.print(f"[green]Deleted build {build_id}[/green]")
        else:
            console.print(f"[red]Build {build_id} not found[/red]")
    else:
        console.print("[red]Must specify --build-id, --code, or --all[/red]")
