"""
OAuth2/OIDC integration for MCP servers — Keycloak token validation.

Provides:
  - KeycloakTokenVerifier: Validates tokens via RFC 7662 introspection — for
    client_credentials access tokens (weather, stock servers).
  - OIDCIdTokenVerifier: Validates OIDC id_tokens by verifying JWT signature
    against Keycloak's JWKS endpoint — no introspection needed (greeting server).
  - OAuthMiddleware: Legacy Starlette middleware (kept for non-FastMCP services).
"""
from __future__ import annotations

import os
import httpx
import jwt
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


# ── OIDC Id-Token Verifier (JWT/JWKS — no introspection) ─────────────────────

@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    """Create a cached JWKS client for a given URL."""
    return jwt.PyJWKClient(jwks_url, cache_keys=True)


class OIDCIdTokenVerifier(TokenVerifier):
    """
    Validates OIDC id_tokens by verifying the JWT signature against
    Keycloak's JWKS endpoint — no introspection call needed.

    This verifier:
      1. Discovers the JWKS URI and canonical issuer from OIDC discovery
      2. Fetches the signing keys from the JWKS endpoint
      3. Verifies the JWT signature (RS256)
      4. Checks issuer and expiration claims
      5. Returns an AccessToken with user identity from the JWT

    The canonical issuer is read from the OIDC discovery document, so it
    works correctly even when Keycloak is reached via a Docker-internal URL
    but tokens carry the external hostname (--hostname flag).
    """

    def __init__(
        self,
        keycloak_url: str | None = None,
        realm: str | None = None,
    ):
        self._keycloak_url = keycloak_url or KEYCLOAK_URL
        self._realm = realm or KEYCLOAK_REALM
        # Discover canonical issuer and JWKS URI from OIDC config
        oidc = _get_oidc_config(self._keycloak_url, self._realm)
        self._issuer = oidc["issuer"]
        self._jwks_url = oidc.get(
            "jwks_uri",
            f"{self._keycloak_url}/realms/{self._realm}"
            f"/protocol/openid-connect/certs",
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify an OIDC id_token by checking its JWT signature via JWKS."""
        try:
            jwks_client = _get_jwks_client(self._jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={
                    "verify_aud": False,  # id_tokens have varying audiences
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )

            return AccessToken(
                token=token,
                client_id=claims.get("azp", claims.get("sub", "unknown")),
                scopes=claims.get("scope", "").split() if claims.get("scope") else [],
                expires_at=claims.get("exp"),
            )
        except (jwt.InvalidTokenError, jwt.PyJWKClientError, Exception):
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
