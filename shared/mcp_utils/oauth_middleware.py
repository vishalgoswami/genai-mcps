"""
OAuth2/OIDC integration for MCP servers — Keycloak token validation.

Provides:
  - KeycloakTokenVerifier: Implements MCP SDK's TokenVerifier protocol for
    native FastMCP auth integration (the standard way).
  - OAuthMiddleware: Legacy Starlette middleware (kept for non-FastMCP services).

Token verification uses Keycloak's token introspection endpoint, which works
reliably with all grant types including client_credentials (service accounts).
"""
from __future__ import annotations

import os
import httpx
from functools import lru_cache

from mcp.server.auth.provider import AccessToken, TokenVerifier
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"


@lru_cache(maxsize=1)
def _get_oidc_config(keycloak_url: str = KEYCLOAK_URL, realm: str = KEYCLOAK_REALM) -> dict:
    """Fetch OIDC discovery document from Keycloak."""
    url = f"{keycloak_url}/realms/{realm}/.well-known/openid-configuration"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_introspection_endpoint(keycloak_url: str = KEYCLOAK_URL, realm: str = KEYCLOAK_REALM) -> str:
    config = _get_oidc_config(keycloak_url, realm)
    return config.get(
        "introspection_endpoint",
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token/introspect",
    )


# ── MCP SDK native TokenVerifier ─────────────────────────────────────────────
class KeycloakTokenVerifier(TokenVerifier):
    """
    Validates Bearer tokens against Keycloak via token introspection —
    implements the MCP SDK's TokenVerifier protocol for FastMCP native auth.

    Uses the OAuth2 token introspection endpoint (RFC 7662), which works
    with all grant types including client_credentials (service accounts).

    The server's own client_id/client_secret is used to authenticate the
    introspection call (the server acts as a confidential client).
    """

    def __init__(
        self,
        keycloak_url: str | None = None,
        realm: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self._keycloak_url = keycloak_url or KEYCLOAK_URL
        self._realm = realm or KEYCLOAK_REALM
        self._client_id = client_id or os.getenv("OAUTH_CLIENT_ID", "")
        self._client_secret = client_secret or os.getenv("OAUTH_CLIENT_SECRET", "")

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a Bearer token via Keycloak introspection and return AccessToken."""
        try:
            introspect_url = _get_introspection_endpoint(self._keycloak_url, self._realm)
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    introspect_url,
                    data={
                        "token": token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    return None

                info = resp.json()
                if not info.get("active", False):
                    return None

                return AccessToken(
                    token=token,
                    client_id=info.get("client_id", info.get("azp", "unknown")),
                    scopes=info.get("scope", "").split(),
                    expires_at=info.get("exp"),
                )
        except Exception:
            return None


# ── Legacy Starlette middleware (for non-FastMCP services like gateway) ───────
class OAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces OAuth on /mcp paths when enabled."""

    async def dispatch(self, request: Request, call_next):
        if not MCP_AUTH_ENABLED:
            return await call_next(request)

        path = request.url.path
        if path in ("/health", "/healthz", "/ready"):
            return await call_next(request)

        if path.startswith("/mcp"):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "detail": "Bearer token required"},
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'},
                )

            token = auth_header[7:]
            verifier = KeycloakTokenVerifier()
            result = await verifier.verify_token(token)
            if result is None:
                return JSONResponse(
                    status_code=401,
                    content={"error": "invalid_token", "detail": "Token validation failed"},
                    headers={"WWW-Authenticate": 'Bearer realm="mcp", error="invalid_token"'},
                )

            request.state.user = {"sub": result.client_id, "scopes": result.scopes}

        return await call_next(request)
