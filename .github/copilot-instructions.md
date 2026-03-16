# MCP Hub — Project Guidelines

## Architecture

This is a Python monorepo for Model Context Protocol (MCP) servers, clients, a gateway, and a registry.

```
mcps/
├── servers/          # MCP servers — FastMCP + streamable HTTP
│   ├── weather/      # 🔒 OAuth (introspection) — port 9002
│   ├── stock/        # 🔒 OAuth (introspection) — port 9003
│   ├── calculator/   # 🔓 No auth — port 9004
│   └── greeting/     # 🔑 OIDC (JWT/JWKS) — port 9005
├── gateway/          # Smart auth proxy — aggregates tools, handles per-server auth
├── clients/          # Client apps that consume MCP servers
│   ├── adk-agui/     # Google ADK + AG-UI conversational agent (port 8001)
│   ├── cli/          # Interactive terminal REPL
│   └── langgraph/    # LangGraph agent (port 8002)
├── registry/         # Web-based MCP server registry (backend + frontend)
├── shared/           # Shared Python library (mcp_utils) — OAuth verifiers, base classes, types
├── infra/            # Keycloak realm config, centralized credentials template
└── docs/             # Architecture diagrams
```

## Key Design Decisions

- **MCP SDK**: All servers use `mcp.server.fastmcp.FastMCP`. Host/port are constructor kwargs; `run()` only takes `transport`.
- **Gateway uses low-level Server**: The gateway uses `mcp.server.Server` (not `FastMCP`) with `StreamableHTTPSessionManager` for raw argument passthrough — avoids Pydantic schema validation on proxy tool calls. Tool definitions preserve upstream `inputSchema` exactly.
- **Multi-transport**: Every MCP server supports `stdio`, `sse`, and `streamable-http` via `--transport` CLI flag or `MCP_TRANSPORT` env var. Default is `stdio` locally, `streamable-http` in Docker.
- **Dual connectivity**: Clients can connect via the **Gateway** (single URL, centralized routing/auth) or **directly** to individual MCP servers (per-server URLs). The ADK client defaults to direct connections configured via `MCP_SERVERS` JSON.
- **Gateway smart auth proxy**: The gateway handles per-server auth so clients don't have to. Clients send a single OIDC id_token for user identity; the gateway manages OAuth client_credentials for protected servers, passes through id_tokens for OIDC servers, and sends no auth for open servers. Auth type per server is configured in `gateway/config/servers.yaml` via `auth_type: none|oauth|oidc`.
- **Auth via ADC**: Client apps (adk-agui, langgraph) use Google Cloud Application Default Credentials — never API keys. Set `GOOGLE_GENAI_USE_VERTEXAI=true` in `.env`.
- **Three auth strategies**: MCP servers demonstrate three authentication models via `MCP_AUTH_ENABLED`:
  - **None** (calculator): No auth. Open to all callers.
  - **OAuth / introspection** (weather, stock): Uses `KeycloakTokenVerifier` — validates `access_token` via RFC 7662 introspection. Client uses `client_credentials` grant.
  - **OIDC / JWT+JWKS** (greeting): Uses `OIDCIdTokenVerifier` — validates `id_token` JWT signature via JWKS endpoint. Client uses `password` grant with `scope=openid`. Discovers canonical issuer from OIDC discovery to handle Docker hostname mismatch.
  Both verifiers live in `shared/mcp_utils/oauth_middleware.py` and discover endpoints from `/.well-known/openid-configuration`, making them IdP-agnostic.
- **Pluggable MCP client config**: The ADK client (`clients/adk-agui`) uses `MCPServerConfig` with per-server auth control. The `auth` field accepts `false` (no auth), `true`/`"oauth"` (client_credentials), or `"oidc"` (password grant → id_token). Configure via `MCP_SERVERS` JSON array (preferred) or legacy `MCP_SERVER_URLS` comma-separated list.
- **Hatchling builds**: All Python packages use hatchling. Source lives in `src/`, so every `pyproject.toml` needs `[tool.hatch.build.targets.wheel] packages = ["src"]` (or `["mcp_utils"]` for shared).
- **Docker context**: Server Dockerfiles use the repo root as build context (to COPY `shared/`). Use `docker build -f servers/<name>/Dockerfile .` from root. Exception: calculator has no auth, so no `shared/` COPY needed.
- **Docker healthchecks**: Use Python (`urllib.request`) instead of `curl` — `python:3.12-slim` doesn't include curl. Healthchecks treat HTTP 401 as healthy (server is up, just requires auth).

## Port Assignments

| Component | Port | Auth |
|---|---|---|
| Gateway | 8000 | — |
| ADK+AGUI Client | 8001 | — |
| LangGraph Client | 8002 | — |
| Registry Backend | 8080 | — |
| Registry Frontend | 3000 | — |
| Keycloak | 8180 | — |
| Weather Server | 9002 | 🔒 OAuth (introspection) |
| Stock Server | 9003 | 🔒 OAuth (introspection) |
| Calculator Server | 9004 | 🔓 None |
| Greeting Server | 9005 | 🔑 OIDC (JWT/JWKS) |

## Auth Architecture

### Three Token Verification Strategies

**1. No Auth (Calculator)**
- Server accepts all requests without `Authorization` header.

**2. OAuth — Access Token Introspection (Weather, Stock)**
```python
from mcp_utils import KeycloakTokenVerifier
mcp = FastMCP("weather", auth=AuthSettings(...), token_verifier=KeycloakTokenVerifier(...))
```
- Client obtains `access_token` via `client_credentials` grant
- Server introspects the token with Keycloak (RFC 7662) — `POST /token/introspect`
- Server's own `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` authenticate the introspection call

**3. OIDC — Id Token JWT/JWKS Verification (Greeting)**
```python
from mcp_utils import OIDCIdTokenVerifier
mcp = FastMCP("greeting", auth=AuthSettings(...), token_verifier=OIDCIdTokenVerifier(...))
```
- Client obtains `id_token` via `password` grant (or `authorization_code`) with `scope=openid`
- Server verifies JWT signature locally using Keycloak's JWKS endpoint — no introspection call
- `OIDCIdTokenVerifier` discovers the canonical issuer from OIDC discovery (`/.well-known/openid-configuration`) to handle Docker hostname mismatch (`localhost:8180` vs `keycloak:8080`)

### Client-Side Auth (ADK Client)

The ADK client supports three auth modes per server:
- `auth: false` or omitted → no `Authorization` header
- `auth: true` or `auth: "oauth"` → `client_credentials` grant → `access_token` as Bearer
- `auth: "oidc"` → `password` grant with `scope=openid` → `id_token` as Bearer

Uses `OIDC_USERNAME` / `OIDC_PASSWORD` env vars for the password grant flow.

### Gateway Auth (Smart Proxy)

The gateway (`gateway/src/main.py`) handles all upstream auth automatically:
- `auth_type: none` → no Authorization header sent upstream
- `auth_type: oauth` → gateway fetches its own `client_credentials` access_token from Keycloak and sends it as Bearer
- `auth_type: oidc` → gateway passes through the client's OIDC id_token to the upstream server

The gateway uses ASGI middleware (`_TokenExtractMiddleware`) to extract the client's Bearer token into a `ContextVar`, making it available to tool handlers. OAuth tokens are cached with a ~4.5 min TTL.

At startup, the gateway discovers tools from all upstream servers using its own credentials (including password grant for OIDC servers). Tool names are namespaced as `{server}__{tool}` (e.g., `weather__get_forecast`).

### Keycloak Hostname

**Critical**: Keycloak must be started with `--hostname http://localhost:8180 --hostname-backchannel-dynamic true` in docker-compose. Without this, tokens obtained via `localhost:8180` fail introspection when Keycloak is reached as `keycloak:8080` inside Docker (hostname mismatch causes `active: false`).

## Client Configuration

The ADK+AGUI client supports per-server auth via `MCP_SERVERS` JSON:

```env
MCP_SERVERS=[
  {"url": "http://localhost:9002/mcp", "auth": "oauth"},
  {"url": "http://localhost:9003/mcp", "auth": "oauth"},
  {"url": "http://localhost:9004/mcp"},
  {"url": "http://localhost:9005/mcp", "auth": "oidc"}
]
```

Global OAuth/OIDC settings:

```env
KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=mcp
OAUTH_CLIENT_ID=adk-agui-client
OAUTH_CLIENT_SECRET=adk-agui-secret
OIDC_USERNAME=testuser
OIDC_PASSWORD=testpass
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

# Test OAuth (access_token introspection):
TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=client_credentials" -d "client_id=adk-agui-client" \
  -d "client_secret=adk-agui-secret" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -X POST http://localhost:9002/mcp -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'

# Test OIDC (id_token JWT/JWKS):
ID_TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=adk-agui-client" -d "client_secret=adk-agui-secret" \
  -d "username=testuser" -d "password=testpass" -d "scope=openid" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")
curl -X POST http://localhost:9005/mcp -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'

# Test no-auth (calculator):
curl -X POST http://localhost:9004/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
```

## Conventions

- MCP server entry points are registered as `[project.scripts]` in pyproject.toml
- Server names in docker-compose match gateway `config/servers.yaml` (with `auth_type` per server)
- Gateway uses `mcp.server.Server` (low-level) not `FastMCP` — raw dict passthrough for proxy tools
- Gateway exposes tools namespaced as `{server}__{tool}` with original `inputSchema` preserved
- Credentials template is in `infra/credentials.yaml` — never commit real secrets
- `.env` is gitignored; copy from `.env.example`
- Docker-compose Keycloak uses `--hostname http://localhost:8180 --hostname-backchannel-dynamic true`
- Each MCP server in docker-compose has its own `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET`
- Docker healthchecks use `python -c "import urllib.request..."` (not curl)
- Calculator server has no `shared/` dependency (no auth) — its Dockerfile does NOT COPY shared/
- `OIDCIdTokenVerifier` uses `PyJWT[crypto]>=2.8.0` for JWT/JWKS verification
- Registry status checker supports all three auth types (`none`, `oauth`, `oidc`) when probing servers
