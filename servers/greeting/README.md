# Greeting MCP Server

An OIDC-protected MCP server that validates **id_tokens** via JWT/JWKS — no token introspection needed.

## Tools

| Tool | Description |
|------|-------------|
| `greet(name, language)` | Greet someone in 10 languages |
| `farewell(name, language)` | Say farewell in 10 languages |

## Auth Model

Unlike the weather/stock servers (which use RFC 7662 token introspection with `client_credentials` access tokens), this server:

1. Expects an OIDC **id_token** as Bearer token
2. Validates the JWT signature against Keycloak's **JWKS** endpoint
3. Verifies issuer, expiration, and audience claims
4. Extracts user identity (`sub`, `email`) from the token

Clients obtain the id_token via OIDC flows that return user identity (e.g., `password` grant with `scope=openid`, or `authorization_code`).

## Run

```bash
# Local
cd servers/greeting && pip install -e . -e ../../shared && \
  MCP_AUTH_ENABLED=true KEYCLOAK_URL=http://localhost:8180 KEYCLOAK_REALM=mcp \
  greeting-server --transport streamable-http

# Docker (from repo root)
docker build -f servers/greeting/Dockerfile -t mcp-greeting .
docker run -p 9005:9005 -e MCP_AUTH_ENABLED=true mcp-greeting
```

## Port

Default: **9005**
