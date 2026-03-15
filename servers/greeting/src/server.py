"""
Greeting MCP Server — OIDC id_token auth via JWT/JWKS verification.

Exposes tools via MCP:
  - greet(name, language)    → greeting in the chosen language
  - farewell(name, language) → farewell in the chosen language

Unlike the weather/stock servers (which use token introspection),
this server validates OIDC id_tokens by verifying the JWT signature
against Keycloak's JWKS endpoint — no introspection call needed.

Usage:
  greeting-server
  greeting-server --transport streamable-http --host 0.0.0.0 --port 9005
"""
from __future__ import annotations

import argparse
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Greeting MCP Server")
    p.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
    )
    p.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "9005")))
    return p.parse_args()


_args = _parse_args()

_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"
_KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
_KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")


def _build_mcp() -> FastMCP:
    """Build FastMCP instance, with OIDC JWT verification when enabled."""
    kwargs: dict[str, Any] = dict(host=_args.host, port=_args.port)
    if _AUTH_ENABLED:
        from mcp_utils.oauth_middleware import OIDCIdTokenVerifier

        issuer_url = f"{_KEYCLOAK_URL}/realms/{_KEYCLOAK_REALM}"
        resource_url = f"http://localhost:{_args.port}"
        kwargs["auth"] = AuthSettings(
            issuer_url=issuer_url,
            resource_server_url=resource_url,
        )
        kwargs["token_verifier"] = OIDCIdTokenVerifier(
            keycloak_url=_KEYCLOAK_URL,
            realm=_KEYCLOAK_REALM,
        )
        print(f"[greeting] OIDC JWT auth ENABLED — issuer: {issuer_url}")
    return FastMCP("greeting", **kwargs)


mcp = _build_mcp()

# ── Greeting data ────────────────────────────────────────────────────────────
_GREETINGS: dict[str, str] = {
    "english": "Hello",
    "spanish": "Hola",
    "french": "Bonjour",
    "german": "Hallo",
    "japanese": "こんにちは",
    "korean": "안녕하세요",
    "italian": "Ciao",
    "portuguese": "Olá",
    "chinese": "你好",
    "hindi": "नमस्ते",
}

_FAREWELLS: dict[str, str] = {
    "english": "Goodbye",
    "spanish": "Adiós",
    "french": "Au revoir",
    "german": "Auf Wiedersehen",
    "japanese": "さようなら",
    "korean": "안녕히 가세요",
    "italian": "Arrivederci",
    "portuguese": "Adeus",
    "chinese": "再见",
    "hindi": "अलविदा",
}


@mcp.tool()
async def greet(name: str, language: str = "english") -> str:
    """Greet someone in a chosen language.

    Args:
        name: Name of the person to greet
        language: Language for the greeting (english, spanish, french, german, japanese, korean, italian, portuguese, chinese, hindi)
    """
    lang = language.lower()
    greeting = _GREETINGS.get(lang)
    if not greeting:
        available = ", ".join(sorted(_GREETINGS.keys()))
        return f"Unknown language '{language}'. Available: {available}"
    return f"{greeting}, {name}!"


@mcp.tool()
async def farewell(name: str, language: str = "english") -> str:
    """Say farewell to someone in a chosen language.

    Args:
        name: Name of the person to bid farewell
        language: Language for the farewell (english, spanish, french, german, japanese, korean, italian, portuguese, chinese, hindi)
    """
    lang = language.lower()
    fw = _FAREWELLS.get(lang)
    if not fw:
        available = ", ".join(sorted(_FAREWELLS.keys()))
        return f"Unknown language '{language}'. Available: {available}"
    return f"{fw}, {name}!"


def main():
    transport = _args.transport
    print(f"[greeting] Starting with transport={transport}, host={_args.host}, port={_args.port}")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
