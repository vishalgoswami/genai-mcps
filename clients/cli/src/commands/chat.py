"""chat command — launch an interactive supervisor REPL against one or many MCP servers."""
import os
import click
from src.repl import MCPRepl

# Default: comma-separated list from env, fallback to weather server
DEFAULT_URLS = os.getenv(
    "MCP_SERVER_URLS",
    os.getenv("MCP_SERVER_URL", "http://localhost:9002/mcp"),
)


@click.command()
@click.argument("urls", nargs=-1)
@click.option("--model", default="gemini-2.5-flash", show_default=True, help="Gemini model to use")
def chat(urls: tuple[str, ...], model: str):
    """Start an interactive supervisor chat session.

    Pass one or more MCP server URLs as arguments, or set MCP_SERVER_URLS env var
    (comma-separated). If none provided, uses the default weather server.

    Examples:

        mcp-cli chat http://localhost:9002/mcp http://localhost:9003/mcp

        MCP_SERVER_URLS=http://localhost:9002/mcp,http://localhost:9003/mcp mcp-cli chat
    """
    if urls:
        server_urls = list(urls)
    else:
        server_urls = [u.strip() for u in DEFAULT_URLS.split(",") if u.strip()]

    repl = MCPRepl(server_urls=server_urls, model=model)
    repl.run()
