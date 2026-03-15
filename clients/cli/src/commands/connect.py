"""connect command — verify connectivity to an MCP server."""
import click
import httpx
from rich.console import Console

console = Console()


@click.command()
@click.argument("url")
def connect(url: str):
    """Test connection to an MCP server at URL."""
    try:
        resp = httpx.get(f"{url}/health", timeout=5)
        resp.raise_for_status()
        console.print(f"[green]✓ Connected to {url}[/green]")
        console.print(resp.json())
    except Exception as e:
        console.print(f"[red]✗ Failed to connect: {e}[/red]")
