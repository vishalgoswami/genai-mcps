# MCP Hub — Model Context Protocol Monorepo

A production-ready monorepo for **MCP servers**, **agentic clients**, a **gateway**, and a **web registry** — all wired together with optional **Keycloak OAuth2** security.

## Architecture

Clients can connect to MCP servers in two ways:
- **Via the Gateway** (port 8000) — a single aggregating reverse-proxy that unifies all MCP servers behind one endpoint
- **Directly** to individual MCP servers — each server exposes its own streamable-HTTP endpoint

Both paths support optional OAuth2 Bearer tokens validated by an OIDC-compliant identity provider (Keycloak for development).

```
                          ┌──────────────────────────────────────────┐
                          │              Clients                     │
                          │                                          │
                          │  ┌─────────────┐   ┌─────────────────┐  │
                          │  │  ADK+AGUI   │   │   LangGraph     │  │
                          │  │ (port 8001) │   │  (port 8002)    │  │
                          │  └──────┬──────┘   └───────┬─────────┘  │
                          │         │                  │            │
                          │         │   ┌──────────┐   │            │
                          │         │   │   CLI    │   │            │
                          │         │   │ (REPL)   │   │            │
                          │         │   └────┬─────┘   │            │
                          └─────────┼────────┼─────────┼────────────┘
                                    │        │         │
                Bearer tokens       │        │         │
                (OAuth)             │        │         │
                                    │        │         │
              ┌─────────────────────┼────────┼─────────┼──┐
              │  Path A: Gateway    │        │         │  │
              │  (single endpoint)  ▼        ▼         ▼  │
              │            ┌────────────────────────────┐  │
              │            │        Gateway             │  │
              │            │      (port 8000)           │  │
              │            └────────────┬───────────────┘  │
              │                         │                  │
              └─────────────────────────┼──────────────────┘
                                        │
              ┌─────────── Path B: Direct connections ─────────────┐
              │  (clients connect to each server individually)      │
              │                         │                           │
              │       ┌─────────────────┼─────────────────┐        │
              │       ▼                 ▼                  ▼        │
              │ ┌───────────┐   ┌───────────┐   ┌─────────────────┐│
              │ │  Weather   │   │  Stock    │   │  Your Server    ││
              │ │ MCP Server │   │MCP Server │   │   (plug in!)    ││
              │ │ port 9002  │   │ port 9003 │   │   port 900x     ││
              │ └───────────┘   └───────────┘   └─────────────────┘│
              └────────────────────────────────────────────────────┘
                                        │
                         ┌──────────────┼──────────────┐
                         ▼                             ▼
               ┌──────────────────┐          ┌─────────────────┐
               │    Keycloak      │          │   MCP Registry   │
               │   OIDC Provider  │          │ Backend + React  │
               │   (port 8180)    │          │  (8080 / 3000)   │
               └──────────────────┘          └─────────────────┘
```

**Path A — Gateway**: Clients send all MCP requests to `http://gateway:8000/mcp`. The gateway routes to the correct backend server based on the tool being invoked. This simplifies client config (one URL) and centralizes auth, rate-limiting, and observability.

**Path B — Direct**: Clients connect to each MCP server individually (e.g., `http://localhost:9002/mcp`, `http://localhost:9003/mcp`). This is simpler for local development and gives per-server auth control. The ADK client uses this mode with `MCP_SERVERS` JSON config.

### Component Overview

| Component | Port | Tech | Description |
|---|---|---|---|
| **Weather Server** | 9002 | FastMCP | US weather alerts & forecasts (NWS API) |
| **Stock Server** | 9003 | FastMCP | Stock prices, history, company info |
| **Gateway** | 8000 | FastAPI | Aggregating reverse-proxy for all MCP servers |
| **ADK+AGUI Client** | 8001 | Google ADK + FastAPI | Chat UI with Gemini — calls MCP tools |
| **LangGraph Client** | 8002 | LangGraph + FastAPI | LangGraph-based conversational agent |
| **CLI Client** | — | Python | Interactive terminal REPL for MCP |
| **Registry Backend** | 8080 | FastAPI + SQLite | MCP server catalog API |
| **Registry Frontend** | 3000 | React + Vite | Web UI for browsing MCP servers |
| **Keycloak** | 8180 | Keycloak 25 | OAuth2/OIDC identity provider |

### Data Flow

1. **Client** sends chat message → ADK agent (Gemini) decides which MCP tool to call
2. **Client** fetches OAuth Bearer token from Keycloak (if auth enabled for that server)
3. **Client** calls MCP server via streamable-HTTP with `Authorization: Bearer <token>`
4. **MCP Server** introspects token with Keycloak → validates → executes tool → returns result
5. **Agent** formats and presents the result to the user

### OAuth Architecture

```
Client (adk-agui)                 Keycloak                MCP Server
      │                              │                         │
      │─── client_credentials ──────►│                         │
      │◄── access_token ────────────│                         │
      │                              │                         │
      │─── POST /mcp ───────────────┼────────────────────────►│
      │    Authorization: Bearer T   │                         │
      │                              │◄── introspect(T) ──────│
      │                              │─── active: true ───────►│
      │◄── MCP response ────────────┼────────────────────────│
```

### Why Keycloak? (and using a different IdP in production)

This project uses **Keycloak** as the OIDC identity provider for development and testing. Keycloak was chosen because:

- **Self-contained** — runs as a single Docker container with zero external dependencies, making the development environment fully offline-capable
- **Standards-compliant** — fully implements OAuth 2.0, OpenID Connect, and RFC 7662 token introspection, which the MCP SDK's auth chain relies on
- **Realm export/import** — the entire auth config (clients, roles, users) is captured in `infra/keycloak/realm-export.json` and auto-imported on startup, so every developer gets an identical setup with zero manual configuration
- **Multiple grant types** — supports `client_credentials` (service-to-service), `authorization_code` (interactive), and `password` (testing) out of the box

**In a production environment**, you would typically replace Keycloak with your organization's existing identity provider. The MCP auth integration is designed to work with **any OIDC-compliant IdP** — the only requirement is a standard token introspection endpoint (RFC 7662). Common production alternatives include:

| IdP | Notes |
|---|---|
| **Auth0** | Managed OIDC with built-in introspection |
| **Okta** | Enterprise SSO; introspection via `/oauth2/v1/introspect` |
| **Azure AD (Entra ID)** | Microsoft ecosystem; use `/oauth2/v2.0/introspect` |
| **Google Cloud Identity** | If already using GCP for Vertex AI |
| **AWS Cognito** | If hosting MCP servers on AWS |
| **PingIdentity / ForgeRock** | Enterprise on-prem alternatives |

To swap IdPs, update these environment variables on each MCP server:

```dotenv
KEYCLOAK_URL=https://your-idp.example.com   # base URL of the OIDC provider
KEYCLOAK_REALM=your-realm                    # realm or tenant (IdP-specific)
OAUTH_CLIENT_ID=my-server                    # confidential client for introspection
OAUTH_CLIENT_SECRET=...                      # client secret for introspection
```

The `KeycloakTokenVerifier` in `shared/mcp_utils/oauth_middleware.py` discovers the introspection endpoint automatically via the OIDC discovery document (`/.well-known/openid-configuration`), so it works with any compliant provider despite the "Keycloak" name.

## Repository Structure

```
mcps/
├── servers/              # MCP server implementations
│   ├── weather/          # Weather alerts & forecasts (port 9002)
│   ├── stock/            # Stock market data (port 9003)
│   └── Dockerfile.template
├── gateway/              # Aggregating MCP gateway (port 8000)
├── clients/
│   ├── adk-agui/         # Google ADK + AG-UI chat client (port 8001)
│   ├── cli/              # Terminal REPL client
│   └── langgraph/        # LangGraph agent client (port 8002)
├── registry/
│   ├── backend/          # FastAPI registry API (port 8080)
│   └── frontend/         # React registry UI (port 3000)
├── shared/               # Shared Python lib (mcp_utils) — OAuth, base classes
├── infra/
│   ├── keycloak/         # Keycloak realm config (auto-imported)
│   └── credentials.yaml  # Centralized OAuth credentials template
├── docker-compose.yml    # Full stack orchestration
└── .env.example          # Environment template
```

## Local Development Setup (macOS)

### Prerequisites

- **Python 3.11+** — `brew install python@3.13`
- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Google Cloud CLI** — `brew install google-cloud-sdk` (for Vertex AI / Gemini)

### Step 1 — Clone & configure environment

```bash
git clone https://github.com/vishalgoswami/genai-mcps.git
cd mcps
cp .env.example .env
```

Edit `.env` and set your Google Cloud project:

```dotenv
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MCP_AUTH_ENABLED=true        # set to "false" to skip OAuth entirely
```

### Step 2 — Authenticate with Google Cloud (for Gemini / Vertex AI)

```bash
gcloud auth application-default login
# Verify:
gcloud auth application-default print-access-token
```

### Step 3 — Start Keycloak (OAuth provider)

```bash
# Start Docker Desktop first, then:
docker compose up keycloak -d

# Wait for healthy status (~30–45 seconds):
docker ps --format "table {{.Names}}\t{{.Status}}"
# → mcps-keycloak-1   Up 45 seconds (healthy)
```

Keycloak auto-imports the `mcp` realm with pre-configured clients:

| Client | Secret | Purpose |
|---|---|---|
| `weather-server` | `weather-server-secret` | Weather MCP server (confidential) |
| `stock-server` | `stock-server-secret` | Stock MCP server (confidential) |
| `adk-agui-client` | `adk-agui-secret` | ADK chat client (service account) |
| `mcp-gateway` | `gateway-secret` | Gateway (confidential) |

Admin console: http://localhost:8180 — login `admin` / `admin`

### Step 4 — Start MCP servers

**Option A: Docker (recommended)**

```bash
docker compose up weather-server stock-server -d

# Verify all healthy:
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Option B: Local Python (for development)**

```bash
# Weather server
cd servers/weather
python -m venv .venv && source .venv/bin/activate
pip install -e . -e ../../shared/
MCP_AUTH_ENABLED=true \
OAUTH_CLIENT_ID=weather-server \
OAUTH_CLIENT_SECRET=weather-server-secret \
weather-server --transport streamable-http --port 9002

# Stock server (in another terminal)
cd servers/stock
python -m venv .venv && source .venv/bin/activate
pip install -e . -e ../../shared/
MCP_AUTH_ENABLED=true \
OAUTH_CLIENT_ID=stock-server \
OAUTH_CLIENT_SECRET=stock-server-secret \
stock-server --transport streamable-http --port 9003
```

### Step 5 — Verify OAuth is working

```bash
# Get a token:
TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=adk-agui-client \
  -d client_secret=adk-agui-secret | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Without token → 401:
curl -s -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
# → {"error": "invalid_token", "error_description": "Authentication required"}

# With token → 200:
curl -s -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
# → {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26",...}}
```

### Step 6 — Start the ADK+AGUI chat client

```bash
cd clients/adk-agui
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Configure `clients/adk-agui/.env`:

```dotenv
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
LLM_MODEL=gemini-2.5-flash

# Per-server auth config (recommended):
MCP_SERVERS=[{"url":"http://localhost:9002/mcp","auth":true},{"url":"http://localhost:9003/mcp","auth":true}]

KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=mcp
OAUTH_CLIENT_ID=adk-agui-client
OAUTH_CLIENT_SECRET=adk-agui-secret
```

```bash
adk-agui
# → Uvicorn running on http://0.0.0.0:8001
```

Open http://localhost:8001 in your browser to use the chat UI.

### Step 7 — Full Docker Stack (optional)

```bash
docker compose up -d
# Starts: Keycloak, Weather, Stock, Gateway, Registry
```

## Adding a New MCP Server

### 1. Create the server

```bash
mkdir -p servers/my-server/src
```

`servers/my-server/src/server.py`:

```python
import argparse, os
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings

_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"

def _build_mcp(host: str, port: int) -> FastMCP:
    kwargs = dict(host=host, port=port)
    if _AUTH_ENABLED:
        from mcp_utils.oauth_middleware import KeycloakTokenVerifier
        kc_url = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
        realm  = os.getenv("KEYCLOAK_REALM", "mcp")
        kwargs["auth"] = AuthSettings(
            issuer_url=f"{kc_url}/realms/{realm}",
            resource_server_url=f"http://localhost:{port}",
        )
        kwargs["token_verifier"] = KeycloakTokenVerifier(
            keycloak_url=kc_url, realm=realm,
            client_id=os.getenv("OAUTH_CLIENT_ID", "my-server"),
            client_secret=os.getenv("OAUTH_CLIENT_SECRET", "my-server-secret"),
        )
    return FastMCP("my-server", **kwargs)

p = argparse.ArgumentParser()
p.add_argument("--transport", default=os.getenv("MCP_TRANSPORT", "stdio"),
               choices=["stdio", "sse", "streamable-http"])
p.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
p.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "9004")))
args = p.parse_args()

mcp = _build_mcp(args.host, args.port)

@mcp.tool()
async def my_tool(query: str) -> str:
    """Your tool description."""
    return f"Result for {query}"

def main():
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main()
```

### 2. Register it in the client

Add the server to `clients/adk-agui/.env`:

```dotenv
# Mix auth and no-auth servers freely:
MCP_SERVERS=[
  {"url": "http://localhost:9002/mcp", "auth": true},
  {"url": "http://localhost:9003/mcp", "auth": true},
  {"url": "http://localhost:9004/mcp", "auth": false}
]
```

That's it — the ADK client auto-discovers tools from all configured servers.

### 3. (Optional) Register in Keycloak

If the server requires OAuth, create a client in Keycloak:

1. Open http://localhost:8180 → admin / admin
2. Select the `mcp` realm → Clients → Create client
3. Client ID: `my-server`, Client authentication: ON
4. Credentials tab → copy the secret
5. Set `OAUTH_CLIENT_ID=my-server` and `OAUTH_CLIENT_SECRET=<secret>` for the server

Or add the client to `infra/keycloak/realm-export.json` for automatic import.

### 4. (Optional) Add to Docker Compose

```yaml
  my-server:
    build:
      context: .
      dockerfile: servers/my-server/Dockerfile
    ports:
      - "9004:9004"
    env_file: .env
    environment:
      MCP_AUTH_ENABLED: ${MCP_AUTH_ENABLED:-false}
      KEYCLOAK_URL: http://keycloak:8080
      OAUTH_CLIENT_ID: my-server
      OAUTH_CLIENT_SECRET: my-server-secret
    depends_on:
      keycloak:
        condition: service_healthy
```

## Pluggable MCP Server Configuration

The ADK client supports two configuration formats:

### Per-server auth (recommended)

```dotenv
MCP_SERVERS=[
  {"url": "http://localhost:9002/mcp", "auth": true},
  {"url": "http://localhost:9003/mcp", "auth": true},
  {"url": "http://external-server:8080/mcp", "auth": false}
]
```

Each server independently controls whether OAuth tokens are sent. This is ideal when mixing internal (protected) and external (public) MCP servers.

### Simple mode (all-or-nothing)

```dotenv
MCP_SERVER_URLS=http://localhost:9002/mcp,http://localhost:9003/mcp
MCP_AUTH_ENABLED=true
```

All servers share the same auth setting. Simpler, but less flexible.

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `MCP_SERVERS` | — | JSON array of server configs (per-server auth) |
| `MCP_SERVER_URLS` | `http://localhost:9002/mcp` | Comma-separated MCP server URLs |
| `MCP_AUTH_ENABLED` | `false` | Global OAuth toggle (for simple mode) |
| `KEYCLOAK_URL` | `http://localhost:8180` | Keycloak base URL |
| `KEYCLOAK_REALM` | `mcp` | Keycloak realm name |
| `OAUTH_CLIENT_ID` | varies per component | OAuth client ID |
| `OAUTH_CLIENT_SECRET` | varies per component | OAuth client secret |
| `MCP_TRANSPORT` | `stdio` (local), `streamable-http` (Docker) | MCP transport protocol |
| `MCP_HOST` | `127.0.0.1` | Server bind host |
| `MCP_PORT` | varies | Server bind port |
| `LLM_MODEL` | `gemini-2.5-flash` | Gemini model for ADK agents |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project ID (for Vertex AI) |
| `GOOGLE_GENAI_USE_VERTEXAI` | — | Set `true` for Vertex AI auth |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Authentication required` | Missing or invalid Bearer token | Check token: `curl -s http://localhost:8180/realms/mcp/protocol/openid-connect/token -d grant_type=client_credentials -d client_id=adk-agui-client -d client_secret=adk-agui-secret` |
| Token introspection `active: false` in Docker | Keycloak hostname mismatch | Ensure `--hostname http://localhost:8180 --hostname-backchannel-dynamic true` in Keycloak command |
| `curl: (7) Failed to connect` | Service not running | `docker ps` to check status; `docker compose up <service> -d` |
| Keycloak unhealthy | Slow startup | Wait 30–60s; check `docker logs mcps-keycloak-1` |
| `ModuleNotFoundError: mcp_utils` | Shared lib not installed | `pip install -e ../../shared/` in server venv |

## Changelog

### v0.3.0 — Pluggable Client Config & Architecture Docs

- **Per-server OAuth control**: New `MCPServerConfig` dataclass in the ADK client — each MCP server independently enables/disables OAuth via the `MCP_SERVERS` JSON env var
- **Dual connectivity model**: Clients can connect via the Gateway (single aggregated endpoint) or directly to individual MCP servers
- **IdP-agnostic design**: Documented that Keycloak is the dev IdP; any OIDC-compliant provider (Auth0, Okta, Azure AD, etc.) works in production via standard RFC 7662 introspection
- **Architecture diagram**: Rewritten to show both Gateway and direct connection paths
- **Comprehensive README**: Full local setup guide (7 steps), "Adding a New MCP Server" template, pluggable config docs, env vars reference, troubleshooting table
- **Updated copilot instructions & skill files**: `.github/copilot-instructions.md` and `.github/skills/local-docker-deploy/SKILL.md` reflect all OAuth, dual-connectivity, and Docker patterns

### v0.2.0 — Native OAuth via FastMCP + Keycloak

- **FastMCP native auth**: MCP servers use `AuthSettings` + `KeycloakTokenVerifier` (MCP SDK's `TokenVerifier` protocol) instead of custom middleware
- **RFC 7662 token introspection**: `KeycloakTokenVerifier` validates Bearer tokens via Keycloak's introspection endpoint — works with all grant types including `client_credentials`
- **Per-server OAuth credentials**: Each MCP server in docker-compose has its own `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET`
- **Keycloak hostname fix**: `--hostname http://localhost:8180 --hostname-backchannel-dynamic true` resolves token mismatch between `localhost:8180` (external) and `keycloak:8080` (Docker-internal)
- **Python-based Docker healthchecks**: Replaced `curl` with `urllib.request` — `python:3.12-slim` doesn't include curl; HTTP 401 treated as healthy
- **Keycloak realm auto-import**: `infra/keycloak/realm-export.json` with pre-configured clients, roles, and test users

### v0.1.0 — Multi-Transport MCP Servers + ADK Client

- **Weather & Stock MCP servers**: FastMCP-based servers with `stdio`, `sse`, and `streamable-http` transport via `--transport` CLI flag / `MCP_TRANSPORT` env var
- **Google ADK + AG-UI client**: Supervisor agent with Gemini (Vertex AI), chat UI on port 8001, auto-discovers tools from remote MCP servers via `MCPToolset`
- **Docker deployment**: Server Dockerfiles with repo-root build context (for `shared/` COPY), hatchling builds with `packages = ["src"]`
- **Gateway**: Aggregating reverse-proxy that unifies multiple MCP servers behind a single endpoint
- **Registry**: FastAPI backend + React frontend for browsing/registering MCP servers
- **Shared library**: `mcp_utils` package with base classes, types, and credential helpers

### v0.0.1 — Initial Commit

- Monorepo scaffold: servers, clients, gateway, registry, shared, infra directories
- Basic project structure and build configuration

## License

MIT
