"""
Credential loader — reads centralized credentials.yaml and provides
helpers to fetch client_id / client_secret for any component, plus
an OAuth2 client_credentials token fetcher.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx
import yaml

# Default path — can be overridden via CREDENTIALS_FILE env var
_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "infra" / "credentials.yaml"
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", str(_DEFAULT_PATH))


@lru_cache(maxsize=1)
def load_credentials(path: str | None = None) -> dict:
    """Load and cache the credentials YAML file."""
    p = Path(path) if path else Path(CREDENTIALS_FILE)
    if not p.exists():
        raise FileNotFoundError(f"Credentials file not found: {p}")
    with open(p) as f:
        return yaml.safe_load(f)


def get_keycloak_config(path: str | None = None) -> dict:
    """Return keycloak connection info."""
    creds = load_credentials(path)
    return creds.get("keycloak", {})


def get_server_creds(server_name: str, path: str | None = None) -> dict:
    """Return client_id / client_secret for an MCP server."""
    creds = load_credentials(path)
    return creds.get("servers", {}).get(server_name, {})


def get_gateway_creds(path: str | None = None) -> dict:
    """Return client_id / client_secret for the gateway."""
    creds = load_credentials(path)
    return creds.get("gateway", {})


def get_client_creds(client_name: str, path: str | None = None) -> dict:
    """Return client_id / client_secret for an agentic client."""
    creds = load_credentials(path)
    return creds.get("clients", {}).get(client_name, {})


async def fetch_client_credentials_token(
    client_id: str,
    client_secret: str,
    keycloak_url: Optional[str] = None,
    realm: Optional[str] = None,
) -> str:
    """
    Perform an OAuth2 client_credentials grant against Keycloak and return
    the access_token string.
    """
    kc = get_keycloak_config()
    url = keycloak_url or kc.get("internal_url", kc.get("url", "http://localhost:8180"))
    r = realm or kc.get("realm", "mcp")
    token_url = f"{url}/realms/{r}/protocol/openid-connect/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
