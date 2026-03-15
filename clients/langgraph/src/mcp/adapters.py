"""
MCP ↔ LangChain tool adapter — discovers tools from multiple MCP servers
and merges them into a unified tool list for the LangGraph agent.

Configure via comma-separated MCP_SERVER_URLS env var:
  MCP_SERVER_URLS=http://localhost:9002/mcp,http://localhost:9003/mcp
"""
from __future__ import annotations
import os
from src.mcp.client import MCPClient

_tools_cache: list | None = None

MCP_SERVER_URLS = os.getenv(
    "MCP_SERVER_URLS",
    os.getenv("MCP_SERVER_URL", "http://localhost:9002/mcp"),
)


def _parse_server_urls(urls_str: str) -> list[str]:
    """Parse comma-separated MCP server URLs into a list."""
    return [u.strip() for u in urls_str.split(",") if u.strip()]


def get_mcp_tools() -> list:
    """
    Discover and cache tools from all configured MCP servers.
    Tools from each server are prefixed with the server index to avoid
    name collisions (e.g., server0__get_alerts, server1__get_stock_price).
    """
    global _tools_cache
    if _tools_cache is None:
        server_urls = _parse_server_urls(MCP_SERVER_URLS)
        all_tools = []
        for i, url in enumerate(server_urls):
            try:
                client = MCPClient(url, server_label=f"server{i}")
                tools = client.list_tools_as_langchain()
                all_tools.extend(tools)
                print(f"[langgraph] ✓ {url}: {len(tools)} tool(s)")
            except Exception as e:
                print(f"[langgraph] ✗ {url}: failed — {e}")
        _tools_cache = all_tools
        print(f"[langgraph] Total tools discovered: {len(_tools_cache)}")
    return _tools_cache
