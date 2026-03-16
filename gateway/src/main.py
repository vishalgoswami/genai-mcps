"""
MCP Gateway — Smart Auth Proxy.

A single MCP endpoint that aggregates tools from all upstream MCP servers.
The gateway handles per-server authentication so clients don't have to:

  - none:  No auth headers sent upstream (open servers like calculator)
  - oauth: Gateway fetches its own client_credentials access_token (weather, stock)
  - oidc:  Gateway passes through the client's OIDC id_token (greeting)

Clients only need to send a single OIDC id_token to the gateway (for
user-identity tools). The gateway manages all upstream auth automatically.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import sys
import time
from contextvars import ContextVar

import mcp.types as types
import yaml
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import ASGIApp, Receive, Scope, Send

# Ensure shared lib is importable (Dockerfile copies it to /app/shared)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from mcp_utils.credentials import (  # noqa: E402
    fetch_client_credentials_token,
    fetch_oidc_id_token,
)

# ── Configuration ─────────────────────────────────────────────────────────────
SERVERS_CONFIG = os.getenv(
    "GATEWAY_SERVERS_CONFIG",
    os.path.join(os.path.dirname(__file__), "..", "config", "servers.yaml"),
)
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "mcp-gateway")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "gateway-secret")
OIDC_USERNAME = os.getenv("OIDC_USERNAME", "")
OIDC_PASSWORD = os.getenv("OIDC_PASSWORD", "")
_PORT = int(os.getenv("GATEWAY_PORT", "8000"))


# ── Context variable for incoming client Bearer token ─────────────────────────
# Set by the ASGI middleware on each request; read by tool handlers to
# pass the client's id_token through to OIDC-protected upstream servers.
_incoming_token: ContextVar[str | None] = ContextVar("_incoming_token", default=None)

# ── Token cache for upstream OAuth calls ──────────────────────────────────────
_token_cache: dict[str, tuple[str, float]] = {}  # key → (token, expires_at)


# ── ASGI Middleware — extracts client Bearer token into context var ────────────

class _TokenExtractMiddleware:
    """
    Pure ASGI middleware that reads the Authorization header from every
    incoming HTTP request and stores the Bearer token in a context variable.

    This lets downstream tool handlers access the client's id_token for
    pass-through to OIDC-protected upstream servers.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth.lower().startswith("bearer "):
                _incoming_token.set(auth[7:])
            else:
                _incoming_token.set(None)
        await self.app(scope, receive, send)


# ── Low-level MCP Server ─────────────────────────────────────────────────────
server = Server("mcp-gateway")


def _load_servers_config() -> list[dict]:
    """Load upstream MCP server definitions from YAML."""
    with open(SERVERS_CONFIG) as f:
        data = yaml.safe_load(f)
    return [s for s in data.get("servers", []) if s.get("enabled", True)]


# ── Upstream token helpers ────────────────────────────────────────────────────

async def _get_oauth_token() -> str:
    """Fetch (or return cached) client_credentials access_token for OAuth servers."""
    now = time.time()
    cached = _token_cache.get("oauth")
    if cached and cached[1] > now + 30:  # 30s safety buffer
        return cached[0]

    token = await fetch_client_credentials_token(
        client_id=OAUTH_CLIENT_ID,
        client_secret=OAUTH_CLIENT_SECRET,
        keycloak_url=KEYCLOAK_URL,
        realm=KEYCLOAK_REALM,
    )
    _token_cache["oauth"] = (token, now + 270)  # cache ~4.5 min
    return token


async def _get_discovery_oidc_token() -> str:
    """Fetch id_token for gateway's own use during OIDC server discovery."""
    now = time.time()
    cached = _token_cache.get("oidc_discovery")
    if cached and cached[1] > now + 30:
        return cached[0]

    token = await fetch_oidc_id_token(
        client_id=OAUTH_CLIENT_ID,
        client_secret=OAUTH_CLIENT_SECRET,
        username=OIDC_USERNAME,
        password=OIDC_PASSWORD,
        keycloak_url=KEYCLOAK_URL,
        realm=KEYCLOAK_REALM,
    )
    _token_cache["oidc_discovery"] = (token, now + 270)
    return token


async def _build_upstream_headers(auth_type: str) -> dict[str, str]:
    """Build auth headers for a runtime tool call based on auth_type."""
    if auth_type == "oauth":
        token = await _get_oauth_token()
        return {"Authorization": f"Bearer {token}"}
    if auth_type == "oidc":
        # Pass through the client's id_token
        user_token = _incoming_token.get(None)
        if user_token:
            return {"Authorization": f"Bearer {user_token}"}
        return {}  # no user token — upstream will reject
    return {}  # none


async def _build_discovery_headers(auth_type: str) -> dict[str, str]:
    """Build auth headers for startup discovery (gateway's own tokens)."""
    if auth_type == "oauth":
        token = await _get_oauth_token()
        return {"Authorization": f"Bearer {token}"}
    if auth_type == "oidc" and OIDC_USERNAME and OIDC_PASSWORD:
        token = await _get_discovery_oidc_token()
        return {"Authorization": f"Bearer {token}"}
    return {}


# ── Upstream tool registry ────────────────────────────────────────────────────
# Maps proxy_tool_name → { server_name, server_url, original_name, auth_type }
_tool_registry: dict[str, dict] = {}
# Tool definitions exposed to clients (with upstream schemas preserved)
_upstream_tool_defs: list[types.Tool] = []


async def _discover_upstream_tools():
    """Connect to each upstream MCP server, discover its tools, store definitions."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    servers = _load_servers_config()
    print(f"[gateway] Discovering tools from {len(servers)} upstream server(s)...")
    print(f"[gateway] Auth: oauth→client_credentials  oidc→pass-through  none→open")

    for srv in servers:
        name = srv["name"]
        url = srv["url"]
        auth_type = srv.get("auth_type", "none")
        try:
            headers = await _build_discovery_headers(auth_type)
            async with streamablehttp_client(url, headers=headers) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    for tool in result.tools:
                        proxy_name = f"{name}__{tool.name}"
                        _tool_registry[proxy_name] = {
                            "server_name": name,
                            "server_url": url,
                            "original_name": tool.name,
                            "auth_type": auth_type,
                        }
                        # Preserve the upstream tool's schema exactly
                        _upstream_tool_defs.append(
                            types.Tool(
                                name=proxy_name,
                                description=f"[{name}] {tool.description or tool.name}",
                                inputSchema=tool.inputSchema,
                            )
                        )

                    icon = {"none": "🔓", "oauth": "🔒", "oidc": "🔑"}.get(auth_type, "?")
                    print(f"[gateway]   {icon} {name}: {len(result.tools)} tool(s) — auth={auth_type}")

        except Exception as e:
            print(f"[gateway]   ✗ {name}: failed to discover — {e}")

    # Add the gateway's own meta-tool
    _upstream_tool_defs.append(
        types.Tool(
            name="list_upstream_servers",
            description="List all upstream MCP servers connected to this gateway and their auth types.",
            inputSchema={"type": "object", "properties": {}},
        )
    )


# ── MCP protocol handlers ────────────────────────────────────────────────────

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return all discovered upstream tools plus the gateway's own tools."""
    return _upstream_tool_defs


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Route tool calls to upstream servers with appropriate auth."""
    arguments = arguments or {}

    # Gateway meta-tool
    if name == "list_upstream_servers":
        servers = _load_servers_config()
        lines = ["Connected upstream MCP servers:"]
        for s in servers:
            auth_type = s.get("auth_type", "none")
            icon = {"none": "🔓", "oauth": "🔒", "oidc": "🔑"}.get(auth_type, "?")
            lines.append(
                f"  {icon} {s['name']}: {s['url']} [{auth_type}]"
                f" — {s.get('description', '')}"
            )
        return [types.TextContent(type="text", text="\n".join(lines))]

    # Proxy to upstream server
    if name not in _tool_registry:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    result_text = await _call_upstream(name, arguments)
    return [types.TextContent(type="text", text=result_text)]


async def _call_upstream(proxy_name: str, arguments: dict) -> str:
    """Forward a tool call to the upstream MCP server with appropriate auth."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    info = _tool_registry[proxy_name]
    url = info["server_url"]
    auth_type = info["auth_type"]
    original_name = info["original_name"]

    # For OIDC tools, verify the client provided an id_token
    if auth_type == "oidc" and not _incoming_token.get(None):
        return (
            f"Error: Tool '{original_name}' on '{info['server_name']}' requires user "
            f"authentication. Send an OIDC id_token as "
            f"'Authorization: Bearer <id_token>' to the gateway."
        )

    headers = await _build_upstream_headers(auth_type)

    async with streamablehttp_client(url, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(original_name, arguments=arguments)
            if result.content:
                return result.content[0].text
            return "(empty)"


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import uvicorn

    asyncio.run(_discover_upstream_tools())

    print(f"[gateway] Starting smart auth proxy on :{_PORT}")
    print(f"[gateway] Clients: send OIDC id_token for user-identity tools")
    print(f"[gateway] Gateway handles all upstream auth automatically")

    # Build the MCP streamable-HTTP app using low-level Server
    session_manager = StreamableHTTPSessionManager(app=server)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    starlette_app = Starlette(
        routes=[Mount("/mcp", app=session_manager.handle_request)],
        lifespan=lifespan,
    )

    # Wrap with token-extraction middleware
    wrapped = _TokenExtractMiddleware(starlette_app)

    uvicorn.run(wrapped, host="0.0.0.0", port=_PORT)


if __name__ == "__main__":
    main()
