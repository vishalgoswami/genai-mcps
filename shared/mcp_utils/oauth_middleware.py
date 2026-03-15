"""
OAuth2/OIDC middleware for MCP servers — validates Bearer tokens against Keycloak.

Gated by MCP_AUTH_ENABLED env var. When disabled, all requests pass through.
When enabled, every request to /mcp must carry a valid Bearer token.
"""
from __future__ import annotations
import os
import httpx
from functools import lru_cache
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"


@lru_cache(maxsize=1)
def _get_oidc_config() -> dict:
    """Fetch OIDC discovery document from Keycloak."""
    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=1)
def _get_jwks_uri() -> str:
    return _get_oidc_config()["jwks_uri"]


@lru_cache(maxsize=1)
def _get_userinfo_endpoint() -> str:
    return _get_oidc_config()["userinfo_endpoint"]


async def _validate_token(token: str) -> dict | None:
    """
    Validate token by calling the Keycloak userinfo endpoint (introspection-lite).
    Returns user info dict if valid, None otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _get_userinfo_endpoint(),
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception:
        return None


class OAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces OAuth on /mcp paths when enabled."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth if disabled or if it's a health check
        if not MCP_AUTH_ENABLED:
            return await call_next(request)

        path = request.url.path
        if path in ("/health", "/healthz", "/ready"):
            return await call_next(request)

        # Require auth for MCP endpoints
        if path.startswith("/mcp"):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "detail": "Bearer token required"},
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'},
                )

            token = auth_header[7:]
            user_info = await _validate_token(token)
            if user_info is None:
                return JSONResponse(
                    status_code=401,
                    content={"error": "invalid_token", "detail": "Token validation failed"},
                    headers={"WWW-Authenticate": 'Bearer realm="mcp", error="invalid_token"'},
                )

            # Attach user info to request state for downstream use
            request.state.user = user_info

        return await call_next(request)
