"""MCP CLI — entry point."""
import click
from src.commands.connect import connect
from src.commands.tools import tools
from src.commands.chat import chat
from dotenv import load_dotenv

load_dotenv()


@click.group()
def cli():
    """MCP CLI — interact with any MCP server from your terminal."""


cli.add_command(connect)
cli.add_command(tools)
cli.add_command(chat)

if __name__ == "__main__":
    cli()
