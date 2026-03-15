"""mcp_shared — re-exports for convenience."""
from .types import ToolDef, ToolCallResult
from .client_base import BaseMCPClient
from .server_base import BaseMCPServer
from .oauth_middleware import OAuthMiddleware
from .credentials import (
    load_credentials,
    get_keycloak_config,
    get_server_creds,
    get_gateway_creds,
    get_client_creds,
    fetch_client_credentials_token,
)

__all__ = [
    "ToolDef",
    "ToolCallResult",
    "BaseMCPClient",
    "BaseMCPServer",
    "OAuthMiddleware",
    "load_credentials",
    "get_keycloak_config",
    "get_server_creds",
    "get_gateway_creds",
    "get_client_creds",
    "fetch_client_credentials_token",
]
