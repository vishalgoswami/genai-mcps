"""
MCP Gateway — aggregating MCP proxy.

Connects to upstream MCP servers (weather, stock, etc.) via streamable HTTP,
discovers their tools, and re-exposes them as a single unified MCP endpoint.
Authenticates with upstream servers using OAuth2 client_credentials when enabled.
"""
from __future__ import annotations

import asyncio
import os
import sys

import yaml
from mcp.server.fastmcp import FastMCP

# Ensure shared lib is importable (Dockerfile copies it to /app/shared)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from mcp_utils.credentials import get_gateway_creds, fetch_client_credentials_token  # noqa: E402

# ── Load server config ────────────────────────────────────────────────────────
SERVERS_CONFIG = os.getenv("GATEWAY_SERVERS_CONFIG", os.path.join(os.path.dirname(__file__), "..", "config", "servers.yaml"))
MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"

# ── FastMCP instance for the gateway itself ──────────────────────────────────
mcp = FastMCP("mcp-gateway")


def _load_servers_config() -> list[dict]:
    """Load upstream MCP server definitions from YAML."""
    with open(SERVERS_CONFIG) as f:
        data = yaml.safe_load(f)
    return [s for s in data.get("servers", []) if s.get("enabled", True)]


# ── Upstream tool registry ───────────────────────────────────────────────────
# Maps tool_name → { "server_name": ..., "server_url": ..., "original_name": ... }
_tool_registry: dict[str, dict] = {}


async def _discover_upstream_tools():
    """
    Connect to each upstream MCP server, discover its tools, and register
    proxy wrappers on this gateway's FastMCP instance.
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    servers = _load_servers_config()
    print(f"[gateway] Discovering tools from {len(servers)} upstream server(s)...")

    for server in servers:
        name = server["name"]
        url = server["url"]
        try:
            # Get OAuth token for upstream if auth is enabled
            headers = {}
            if MCP_AUTH_ENABLED and server.get("auth", False):
                gw_creds = get_gateway_creds()
                token = await fetch_client_credentials_token(
                    client_id=gw_creds["client_id"],
                    client_secret=gw_creds["client_secret"],
                )
                headers["Authorization"] = f"Bearer {token}"

            async with streamablehttp_client(url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    for tool in result.tools:
                        # Prefix tool name with server name to avoid collisions
                        proxy_name = f"{name}__{tool.name}"
                        _tool_registry[proxy_name] = {
                            "server_name": name,
                            "server_url": url,
                            "original_name": tool.name,
                            "auth": server.get("auth", False),
                        }
                        # Dynamically register a proxy tool on the gateway
                        _register_proxy_tool(proxy_name, tool)
                    print(f"[gateway]   ✓ {name}: {len(result.tools)} tool(s) at {url}")

        except Exception as e:
            print(f"[gateway]   ✗ {name}: failed to discover tools — {e}")


def _register_proxy_tool(proxy_name: str, tool):
    """Dynamically register a proxy tool that forwards calls upstream."""
    description = f"[{_tool_registry[proxy_name]['server_name']}] {tool.description or tool.name}"
    input_schema = tool.inputSchema or {"type": "object", "properties": {}}

    # Build parameter info for the tool wrapper
    props = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    # Create a closure that captures the proxy_name
    async def _proxy_call(proxy_name=proxy_name, **kwargs) -> str:
        return await _call_upstream(proxy_name, kwargs)

    # Register with FastMCP
    mcp.tool(name=proxy_name, description=description)(_proxy_call)


async def _call_upstream(proxy_name: str, arguments: dict) -> str:
    """Forward a tool call to the upstream MCP server."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    info = _tool_registry[proxy_name]
    url = info["server_url"]
    original_name = info["original_name"]

    headers = {}
    if MCP_AUTH_ENABLED and info.get("auth", False):
        gw_creds = get_gateway_creds()
        token = await fetch_client_credentials_token(
            client_id=gw_creds["client_id"],
            client_secret=gw_creds["client_secret"],
        )
        headers["Authorization"] = f"Bearer {token}"

    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(original_name, arguments=arguments)
            if result.content:
                return result.content[0].text
            return "(empty)"


# ── Also expose a plain list-servers endpoint ────────────────────────────────
@mcp.tool()
async def list_upstream_servers() -> str:
    """List all upstream MCP servers connected to this gateway."""
    servers = _load_servers_config()
    lines = ["Connected upstream MCP servers:"]
    for s in servers:
        lines.append(f"  • {s['name']}: {s['url']} — {s.get('description', '')}")
    return "\n".join(lines)


# ── Entry point ──────────────────────────────────────────────────────────────
def main():
    # Discover upstream tools before starting
    asyncio.run(_discover_upstream_tools())

    port = int(os.getenv("GATEWAY_PORT", "8000"))

    if MCP_AUTH_ENABLED:
        from mcp_utils.oauth_middleware import OAuthMiddleware
        from starlette.middleware import Middleware

        print(f"[gateway] Starting MCP proxy on :{port} (OAuth enabled)")
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=port,
            middleware=[Middleware(OAuthMiddleware)],
        )
    else:
        print(f"[gateway] Starting MCP proxy on :{port} (OAuth disabled)")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
