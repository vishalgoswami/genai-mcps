"""
Google ADK supervisor agent with pluggable multi-server MCP tool integration.

Connects to one or many remote MCP servers via streamable HTTP,
discovers all available tools, and acts as a supervisor agent that
can route user queries to the right tools across any configured server.

Each server can independently have OAuth enabled or disabled, making it
easy to mix public and protected servers.

─── Configuration ─────────────────────────────────────────────────────────

Option 1 — JSON config (recommended, per-server auth control):

  MCP_SERVERS='[
    {"url": "http://localhost:9002/mcp", "auth": true},
    {"url": "http://localhost:9003/mcp", "auth": true},
    {"url": "http://localhost:9004/mcp", "auth": false}
  ]'

  Each entry supports:
    url   (required) — MCP server URL
    auth  (optional) — true/false, default false

Option 2 — Simple comma-separated URLs (all-or-nothing auth via MCP_AUTH_ENABLED):

  MCP_SERVER_URLS=http://localhost:9002/mcp,http://localhost:9003/mcp
  MCP_AUTH_ENABLED=true   # applies to ALL servers

Global OAuth settings (used when auth=true for a server):
  KEYCLOAK_URL, KEYCLOAK_REALM, OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import httpx
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


# ── Global OAuth settings ────────────────────────────────────────────────────
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "adk-agui-client")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "adk-agui-secret")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server connection."""
    url: str
    auth: bool = False
    headers: dict[str, str] = field(default_factory=dict)


def _load_server_configs() -> list[MCPServerConfig]:
    """
    Load MCP server configurations from environment.

    Supports two formats:
      1. MCP_SERVERS — JSON array with per-server auth control (preferred)
      2. MCP_SERVER_URLS — comma-separated URLs, global MCP_AUTH_ENABLED flag
    """
    # Option 1: JSON config (per-server auth)
    raw_json = os.getenv("MCP_SERVERS")
    if raw_json:
        entries = json.loads(raw_json)
        return [
            MCPServerConfig(url=e["url"], auth=e.get("auth", False))
            for e in entries
        ]

    # Option 2: Comma-separated URLs (legacy, all-or-nothing auth)
    urls_str = os.getenv(
        "MCP_SERVER_URLS",
        os.getenv("MCP_SERVER_URL", "http://localhost:9002/mcp"),
    )
    global_auth = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"
    return [
        MCPServerConfig(url=u.strip(), auth=global_auth)
        for u in urls_str.split(",") if u.strip()
    ]


_token_cache: str | None = None


def _fetch_oauth_token() -> str:
    """Perform OAuth2 client_credentials grant against Keycloak (cached)."""
    global _token_cache
    if _token_cache:
        return _token_cache

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
    _token_cache = resp.json()["access_token"]
    print(f"[adk-agui] OAuth token acquired from {token_url}")
    return _token_cache


def build_agent() -> LlmAgent:
    """
    Create an ADK supervisor agent with tools auto-discovered from
    all configured MCP servers (streamable HTTP).

    Each server's OAuth is controlled independently via its config.
    """
    configs = _load_server_configs()
    mcp_toolsets: list[MCPToolset] = []

    for cfg in configs:
        headers: dict[str, str] = dict(cfg.headers)
        if cfg.auth:
            token = _fetch_oauth_token()
            headers["Authorization"] = f"Bearer {token}"

        mcp_toolsets.append(
            MCPToolset(
                connection_params=StreamableHTTPConnectionParams(
                    url=cfg.url,
                    headers=headers or None,
                ),
            )
        )
        label = "🔒 auth" if cfg.auth else "🔓 public"
        print(f"[adk-agui]   {label}  {cfg.url}")

    print(f"[adk-agui] Configured {len(configs)} MCP server(s)")

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
