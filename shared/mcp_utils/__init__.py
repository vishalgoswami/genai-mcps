"""mcp_shared — re-exports for convenience."""
from .types import ToolDef, ToolCallResult
from .client_base import BaseMCPClient
from .oauth_middleware import OAuthMiddleware, KeycloakTokenVerifier, OIDCIdTokenVerifier
from .credentials import (
    load_credentials,
    get_keycloak_config,
    get_server_creds,
    get_gateway_creds,
    get_client_creds,
    fetch_client_credentials_token,
    fetch_oidc_id_token,
)

# server_base depends on fastapi which is not installed in all environments
try:
    from .server_base import BaseMCPServer
except ImportError:
    BaseMCPServer = None  # type: ignore[assignment,misc]

__all__ = [
    "ToolDef",
    "ToolCallResult",
    "BaseMCPClient",
    "BaseMCPServer",
    "OAuthMiddleware",
    "KeycloakTokenVerifier",
    "OIDCIdTokenVerifier",
    "load_credentials",
    "get_keycloak_config",
    "get_server_creds",
    "get_gateway_creds",
    "get_client_creds",
    "fetch_client_credentials_token",
    "fetch_oidc_id_token",
]
