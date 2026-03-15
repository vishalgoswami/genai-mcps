"""
Google ADK supervisor agent with multi-server MCP tool integration.

Connects to one or many remote MCP servers via streamable HTTP,
discovers all available tools, and acts as a supervisor agent that
can route user queries to the right tools across any configured server.

When MCP_AUTH_ENABLED=true, performs a client_credentials OAuth2 grant
against Keycloak and passes the Bearer token to every MCP server.

Configure servers via comma-separated MCP_SERVER_URLS env var:
  MCP_SERVER_URLS=http://localhost:9002/mcp,http://localhost:9003/mcp
"""
from __future__ import annotations

import os

import httpx
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


# ── Configuration ────────────────────────────────────────────────────────────
MCP_SERVER_URLS = os.getenv(
    "MCP_SERVER_URLS",
    os.getenv("MCP_SERVER_URL", "http://localhost:9002/mcp"),
)
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

# OAuth settings (optional)
MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "adk-agui-client")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "adk-agui-secret")


def _parse_server_urls(urls_str: str) -> list[str]:
    """Parse comma-separated MCP server URLs into a list."""
    return [u.strip() for u in urls_str.split(",") if u.strip()]


def _fetch_oauth_token() -> str:
    """Perform OAuth2 client_credentials grant against Keycloak (synchronous)."""
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    resp = httpx.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
        },
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[adk-agui] OAuth token acquired from {token_url}")
    return token


def build_agent() -> LlmAgent:
    """
    Create an ADK supervisor agent with tools auto-discovered from
    all configured MCP servers (streamable HTTP).

    When MCP_AUTH_ENABLED=true, fetches a Bearer token from Keycloak
    via client_credentials grant and injects it into every MCP connection.
    """
    server_urls = _parse_server_urls(MCP_SERVER_URLS)

    # Build auth headers if OAuth is enabled
    headers: dict[str, str] | None = None
    if MCP_AUTH_ENABLED:
        token = _fetch_oauth_token()
        headers = {"Authorization": f"Bearer {token}"}
        print("[adk-agui] OAuth enabled — Bearer token will be sent to all MCP servers")

    # Create one MCPToolset per server
    mcp_toolsets = [
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=url,
                headers=headers,
            ),
        )
        for url in server_urls
    ]

    server_list = "\n".join(f"  - {url}" for url in server_urls)
    print(f"[adk-agui] Connecting to {len(server_urls)} MCP server(s):\n{server_list}")

    agent = LlmAgent(
        name="mcp_supervisor",
        model=LLM_MODEL,
        description="A supervisor agent that routes queries across multiple MCP servers.",
        instruction=(
            "You are a helpful supervisor assistant connected to multiple MCP tool servers. "
            "You have access to tools from different domains (weather, stock prices, etc.). "
            "Analyze the user's question and use the most appropriate tool(s) to answer. "
            "If a question spans multiple domains, call tools from different servers as needed. "
            "Always explain what you are doing before calling a tool. "
            "If no tool is relevant, answer from your own knowledge and say so."
        ),
        tools=mcp_toolsets,
    )
    return agent
