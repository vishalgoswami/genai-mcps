# MCP Hub — Project Guidelines

## Architecture

This is a Python monorepo for Model Context Protocol (MCP) servers, clients, a gateway, and a registry.

```
mcps/
├── servers/          # MCP servers (weather, stock, …) — FastMCP + streamable HTTP
├── gateway/          # Aggregating reverse-proxy that unifies multiple MCP servers
├── clients/          # Client apps that consume MCP servers
│   ├── adk-agui/     # Google ADK + AG-UI conversational agent (port 8001)
│   ├── cli/          # Interactive terminal REPL
│   └── langgraph/    # LangGraph agent (port 8002)
├── registry/         # Web-based MCP server registry (backend + frontend)
├── shared/           # Shared Python library (mcp_utils) — OAuth middleware, base classes, types
├── infra/            # Keycloak realm config, centralized credentials template
└── docs/             # Architecture diagrams
```

## Key Design Decisions

- **MCP SDK**: All servers use `mcp.server.fastmcp.FastMCP`. Host/port are constructor kwargs; `run()` only takes `transport`.
- **Multi-transport**: Every MCP server supports `stdio`, `sse`, and `streamable-http` via `--transport` CLI flag or `MCP_TRANSPORT` env var. Default is `stdio` locally, `streamable-http` in Docker.
- **Dual connectivity**: Clients can connect via the **Gateway** (single URL, centralized routing/auth) or **directly** to individual MCP servers (per-server URLs). The ADK client defaults to direct connections configured via `MCP_SERVERS` JSON.
- **Auth via ADC**: Client apps (adk-agui, langgraph) use Google Cloud Application Default Credentials — never API keys. Set `GOOGLE_GENAI_USE_VERTEXAI=true` in `.env`.
- **OAuth via OIDC (optional)**: MCP servers use FastMCP's native auth (`AuthSettings` + `token_verifier`) powered by `KeycloakTokenVerifier` in `shared/mcp_utils/oauth_middleware.py`. Enable with `MCP_AUTH_ENABLED=true`. Token validation uses RFC 7662 introspection (works with all grant types including `client_credentials`). Keycloak is the dev IdP; any OIDC-compliant provider (Auth0, Okta, Azure AD, etc.) can be used in production — the verifier discovers the introspection endpoint from `/.well-known/openid-configuration`.
- **Pluggable MCP client config**: The ADK client (`clients/adk-agui`) uses `MCPServerConfig` with per-server auth control. Configure via `MCP_SERVERS` JSON array (preferred) or legacy `MCP_SERVER_URLS` comma-separated list. See "Client Configuration" section below.
- **Hatchling builds**: All Python packages use hatchling. Source lives in `src/`, so every `pyproject.toml` needs `[tool.hatch.build.targets.wheel] packages = ["src"]` (or `["mcp_utils"]` for shared).
- **Docker context**: Server Dockerfiles use the repo root as build context (to COPY `shared/`). Use `docker build -f servers/<name>/Dockerfile .` from root.
- **Docker healthchecks**: Use Python (`urllib.request`) instead of `curl` — `python:3.12-slim` doesn't include curl. Healthchecks treat HTTP 401 as healthy (server is up, just requires auth).

## Port Assignments

| Component | Port |
|---|---|
| Gateway | 8000 |
| ADK+AGUI Client | 8001 |
| LangGraph Client | 8002 |
| Registry Backend | 8080 |
| Registry Frontend | 3000 |
| Keycloak | 8180 |
| MCP Servers | 9001+ (weather=9002, stock=9003) |

## OAuth Architecture

### Server-Side (FastMCP Native Auth)

MCP servers use the MCP SDK's built-in auth chain when `MCP_AUTH_ENABLED=true`:

```python
from mcp_utils import KeycloakTokenVerifier
from mcp.server.auth.settings import AuthSettings

mcp = FastMCP(
    "my-server",
    auth=AuthSettings(
        issuer_url=f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}",
        resource_server_url=f"http://localhost:{port}",
    ),
    token_verifier=KeycloakTokenVerifier(),
)
```

`KeycloakTokenVerifier` implements the MCP SDK's `TokenVerifier` protocol using Keycloak's introspection endpoint. The server's own `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` authenticate the introspection call.

### Client-Side (Per-Server Auth)

The ADK client uses `client_credentials` grant to obtain tokens, then sends `Authorization: Bearer <token>` headers per-server. Each server's auth is independently controllable.

### Keycloak Hostname

**Critical**: Keycloak must be started with `--hostname http://localhost:8180 --hostname-backchannel-dynamic true` in docker-compose. Without this, tokens obtained via `localhost:8180` fail introspection when Keycloak is reached as `keycloak:8080` inside Docker (hostname mismatch causes `active: false`).

## Client Configuration

The ADK+AGUI client supports two config formats via environment variables:

**Option 1 — JSON array (recommended, per-server auth):**

```env
MCP_SERVERS=[
  {"url": "http://localhost:9002/mcp", "auth": true},
  {"url": "http://localhost:9003/mcp", "auth": true},
  {"url": "http://localhost:9004/mcp", "auth": false}
]
```

**Option 2 — Comma-separated URLs (legacy, all-or-nothing):**

```env
MCP_SERVER_URLS=http://localhost:9002/mcp,http://localhost:9003/mcp
MCP_AUTH_ENABLED=true
```

Global OAuth settings for authenticated servers:

```env
KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=mcp
OAUTH_CLIENT_ID=adk-agui-client
OAUTH_CLIENT_SECRET=adk-agui-secret
```

## Code Style

- Python 3.11+, type hints everywhere
- FastAPI for HTTP services, Pydantic for schemas
- `async def` for all tool implementations
- Keep MCP tool functions in `src/server.py` for each server
- Environment config via `python-dotenv` + `.env` files

## Build & Test

```bash
# Any server or client
cd servers/weather && pip install -e . && weather-server
cd clients/adk-agui && pip install -e . && adk-agui

# Docker (from repo root)
docker build -f servers/weather/Dockerfile -t mcp-weather .
docker run -p 9002:9002 mcp-weather

# Full stack
docker compose up

# Test OAuth-protected endpoint
TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=client_credentials" -d "client_id=mcp-server" \
  -d "client_secret=changeme" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -X POST http://localhost:9002/mcp -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
```

## Conventions

- MCP server entry points are registered as `[project.scripts]` in pyproject.toml
- Server names in docker-compose match gateway `config/servers.yaml`
- Credentials template is in `infra/credentials.yaml` — never commit real secrets
- `.env` is gitignored; copy from `.env.example`
- Docker-compose Keycloak uses `--hostname http://localhost:8180 --hostname-backchannel-dynamic true`
- Each MCP server in docker-compose has its own `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET`
- Docker healthchecks use `python -c "import urllib.request..."` (not curl)
