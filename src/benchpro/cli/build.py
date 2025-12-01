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
def build_cli():
    """Manage application builds"""
    pass

@build_cli.command(name="run")
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Simulate build")
@click.pass_context
def run_build(ctx, config_file, dry_run):
    """Build an application from a config file"""
    try:
        # Get config
        config = ctx.obj['config']
        # Resolve config file
        config_path = Resolver.resolve_profile(config_file)
        if not config_path:
             raise FileNotFoundError(f"Profile not found: {config_file}")

        # Load config
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        
        app_config = AppConfig(**config_data)
        
        # Load template
        template_path = Path(app_config.build_template)
        if not template_path.exists():
            # Try relative to config file
            template_path = Path(config_file).parent / app_config.build_template
            
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {app_config.build_template}")
            
        with open(template_path, "r") as f:
            template_content = f.read()
            
        # Render build script
        context = app_config.model_dump()
        
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
        
        engine = TemplateEngine(context)
        build_script = engine.render(template_content)
        
        # Create build task
        task_id = f"build_{app_config.name}_{app_config.version}_{int(datetime.now().timestamp())}"
        
        # Create a temporary script file
        # Use configured root_dir for workspaces
        root_dir = Path(config.defaults.get("root_dir", Path.cwd() / "benchpro"))
        build_dir = root_dir / "workspaces" / task_id
        build_dir.mkdir(parents=True, exist_ok=True)
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
            
            # Generate module file
            module_content = module_handler.generate_module_file(
                name=app_config.name,
                version=app_config.version,
                modules=app_config.modules,
                paths=[f"{install_dir}/bin"],
                env_vars=env_vars
            )
            
            module_file = build_dir / f"{app_config.name}.lua"
            with open(module_file, "w") as f:
                f.write(module_content)
                
            # Update activation script to use module
            # We use 'module use' to add the build dir to module path
            build.activation_script = f"module use {build_dir} && module load {app_config.name}"
            
            store = ResultStore()
            store.save_build(build)
            console.print(f"Registered build {task_id}")
            
        else:
            console.print(f"[red]Build failed with exit code {task.exit_code}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error building app: {e}[/red]")
        # import traceback
        # traceback.print_exc()

@build_cli.command(name="list")
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
