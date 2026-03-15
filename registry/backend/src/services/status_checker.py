"""Background task that polls registered MCP servers and updates their status.

Probes each server using the MCP JSON-RPC protocol:
  1. POST initialize → get session ID
  2. POST tools/list  → count tools

For servers with auth_type=oauth, a Bearer token is obtained from
Keycloak via client_credentials grant before probing.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src import models

_scheduler = AsyncIOScheduler()
INTERVAL = int(os.getenv("STATUS_CHECK_INTERVAL", "60"))

# Keycloak / OAuth settings (for probing protected servers)
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
REGISTRY_OAUTH_CLIENT_ID = os.getenv("REGISTRY_OAUTH_CLIENT_ID", "mcp-registry")
REGISTRY_OAUTH_CLIENT_SECRET = os.getenv("REGISTRY_OAUTH_CLIENT_SECRET", "registry-secret")

_MCP_INIT_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "mcp-registry", "version": "0.1.0"},
    },
}

_MCP_TOOLS_LIST_BODY = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
}


async def _fetch_oauth_token() -> str:
    """Obtain a Bearer token from Keycloak via client_credentials grant."""
    token_url = (
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": REGISTRY_OAUTH_CLIENT_ID,
                "client_secret": REGISTRY_OAUTH_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _check_all():
    db: Session = SessionLocal()
    try:
        servers = db.query(models.MCPServer).all()
        for server in servers:
            status, tools_count = await _probe(server.url, server.auth_type)
            server.status = status
            server.tools_count = tools_count
            server.last_checked = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _parse_sse_json(text: str) -> dict | None:
    """Extract JSON from an SSE or plain-JSON response body."""
    import json as _json

    stripped = text.strip()
    # Plain JSON
    if stripped.startswith("{"):
        return _json.loads(stripped)
    # SSE: look for `data: {...}` lines
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: ") and line[6:].strip().startswith("{"):
            return _json.loads(line[6:])
    return None


async def _probe(url: str, auth_type: str = "none") -> tuple[str, int]:
    """Probe an MCP server using JSON-RPC initialize + tools/list."""
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        # Get OAuth token if server requires it
        if auth_type == "oauth":
            token = await _fetch_oauth_token()
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=10) as client:
            # Step 1: initialize → get Mcp-Session-Id
            resp = await client.post(url, json=_MCP_INIT_BODY, headers=headers)
            if resp.status_code == 401:
                return "auth_error", 0
            resp.raise_for_status()

            session_id = resp.headers.get("mcp-session-id", "")

            # Step 2: tools/list
            if session_id:
                headers["mcp-session-id"] = session_id

            resp = await client.post(url, json=_MCP_TOOLS_LIST_BODY, headers=headers)
            resp.raise_for_status()

            data = _parse_sse_json(resp.text)
            if data is None:
                return "online", 0

            tools = data.get("result", {}).get("tools", [])
            return "online", len(tools)
    except Exception:
        return "offline", 0


def start_status_checker(app):
    _scheduler.add_job(_check_all, "interval", seconds=INTERVAL, id="status_checker")
    _scheduler.start()
    app.state.scheduler = _scheduler
