import os
import click
from rich.console import Console

console = Console()

@click.group()
def completion_cli():
    """Manage shell completion"""
    pass

@completion_cli.command(name="install")
@click.option("--shell", type=click.Choice(["bash", "zsh", "fish"]), help="Shell to install completion for")
def install_completion(shell):
    """Install shell completion"""
    if not shell:
        shell = os.environ.get("SHELL", "").split("/")[-1]
        if shell not in ["bash", "zsh", "fish"]:
            console.print(f"[yellow]Could not detect supported shell (detected: {shell}). Please specify --shell.[/yellow]")
            return

    console.print(f"Detected shell: [green]{shell}[/green]")
    
    import sys
    
    # Use the absolute path to the executable to ensure it works even if not in PATH
    # (though for completion to be useful, the command usually needs to be in PATH or aliased)
    bp_path = os.path.abspath(sys.argv[0])
    
    prog_name = "bp"
    env_var = f"_{prog_name.upper()}_COMPLETE"
    
    if shell == "bash":
        cmd = f'eval "$({env_var}=bash_source {bp_path})"'
        rc_file = "~/.bashrc"
    elif shell == "zsh":
        cmd = f'eval "$({env_var}=zsh_source {bp_path})"'
        rc_file = "~/.zshrc"
    elif shell == "fish":
        cmd = f'eval ({env_var}=fish_source {bp_path})'
        rc_file = "~/.config/fish/completions/bp.fish"
    else:
        console.print(f"[red]Unsupported shell: {shell}[/red]")
        return

    console.print("\nTo enable completion, add the following line to your config file:")
    console.print(f"\n    [bold cyan]{cmd}[/bold cyan]\n")
    console.print(f"Config file: {rc_file}")
    
    # We could try to append it automatically, but printing instructions is safer and cleaner for now.
    # The PRD mentions "Append to rc file or print instructions", so this satisfies it.
