"""tools command — list tools exposed by an MCP server."""
import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


@click.command()
@click.argument("url")
def tools(url: str):
    """List all tools available on the MCP server at URL."""
    try:
        resp = httpx.get(f"{url}/tools", timeout=5)
        resp.raise_for_status()
        tool_list = resp.json().get("tools", [])

        table = Table(title=f"Tools @ {url}")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        for t in tool_list:
            table.add_row(t["name"], t.get("description", ""))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
