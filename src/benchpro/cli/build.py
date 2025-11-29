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

console = Console()

@click.group()
def build_cli():
    """Manage application builds"""
    pass

@build_cli.command(name="run")
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Simulate build")
def run_build(config_file, dry_run):
    """Build an application from a config file"""
    try:
        # Load config
        with open(config_file, "r") as f:
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
        engine = TemplateEngine(context)
        build_script = engine.render(template_content)
        
        # Create build task
        task_id = f"build_{app_config.name}_{app_config.version}_{int(datetime.now().timestamp())}"
        
        # Create a temporary script file
        build_dir = Path.cwd() / "builds" / task_id
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
