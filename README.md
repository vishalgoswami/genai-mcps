<p align="center">
  <a href="https://modelcontextprotocol.io">
    <img src="https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/refs/heads/main/docs/specification/assets/images/mcp-cover.png" alt="Model Context Protocol" width="700" />
  </a>
</p>

<p align="center">
  <a href="https://modelcontextprotocol.io/specification/2025-03-26">
    <img src="https://img.shields.io/badge/MCP-2025--03--26-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0wIDE4Yy00LjQyIDAtOC0zLjU4LTgtOHMzLjU4LTggOC04IDggMy41OCA4IDgtMy41OCA4LTggOHoiLz48L3N2Zz4=" alt="MCP spec" />
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
  </a>
  <a href="https://www.docker.com/">
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker" />
  </a>
  <a href="https://cloud.google.com/vertex-ai">
    <img src="https://img.shields.io/badge/Gemini-Vertex_AI-4285F4?logo=google-cloud&logoColor=white" alt="Vertex AI" />
  </a>
  <a href="https://www.keycloak.org/">
    <img src="https://img.shields.io/badge/Keycloak-OIDC-4D4D4D?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0wIDE4Yy00LjQyIDAtOC0zLjU4LTgtOHMzLjU4LTggOC04IDggMy41OCA4IDgtMy41OCA4LTggOHoiLz48L3N2Zz4=" alt="Keycloak" />
  </a>
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License" />
</p>

<h1 align="center">MCP Hub — Enterprise MCP Template</h1>

<p align="center">
  <strong>A production-ready monorepo demonstrating how to build, secure, and operate<br/>
  <a href="https://modelcontextprotocol.io">Model Context Protocol</a> servers in an enterprise environment.</strong>
</p>

<p align="center">
  4 MCP servers &bull; 3 auth strategies &bull; Agentic chat client &bull; Service registry &bull; API gateway &bull; Full OAuth2/OIDC
</p>

---

## What is this?

This is a **template project** that shows you how to set up MCP servers the way they'd run at a real company — with identity providers, multiple auth strategies, a service registry, and an API gateway — all running locally with Docker.

**MCP (Model Context Protocol)** is the open standard for connecting AI models to external tools and data. Think of it as "USB-C for AI" — a single protocol that lets any LLM call any tool. This repo shows you how to go from a toy MCP server running on `stdio` to a fleet of secured, discoverable MCP services that an enterprise platform team would actually deploy.

### Why this template?

Most MCP examples show a single server with `stdio` transport and no security. That's fine for a demo, but in the real world:

- MCP servers live on **cloud infrastructure** (GKE, Cloud Run, ECS) — not your laptop
- They need **authentication** — you can't expose corporate tools to the internet without tokens
- Different servers need **different auth strategies** — some are public, some use machine tokens, some need user identity
- Teams need a **registry** to discover what MCP servers exist and what tools they offer
- A **gateway** simplifies client config and adds observability, rate-limiting, and routing

This template wires all of that together so you can learn the patterns, then adapt them to your own platform.

### What you get

| Component | What it does |
|-----------|-------------|
| **4 MCP Servers** | Weather, stock, calculator, greeting — each with a different auth model |
| **ADK Chat Client** | Google Gemini-powered chat that auto-discovers and calls tools across all servers |
| **API Gateway** | Smart auth proxy — aggregates tools, handles per-server auth automatically |
| **Service Registry** | Web UI + API that catalogs servers, probes their health, and counts their tools |
| **Keycloak IdP** | Local OIDC identity provider with pre-configured clients, users, and realms |
| **Docker Compose** | One command to start the entire stack |

---

## Architecture Overview

### High-Level Data Flow

```
   User
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ADK + AGUI Chat Client (port 8001)                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Gemini 2.5 Flash  (Vertex AI)                        │  │
│  │  "Which tool should I call for this user question?"   │  │
│  └───────────┬───────────────────────────────────────────┘  │
│              │ decides tool + args                           │
│              ▼                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  MCP Toolsets (one per server)                        │  │
│  │  Adds auth headers per server config                  │  │
│  └──┬──────────┬──────────────┬──────────────┬──────────┘  │
│     │          │              │              │              │
└─────┼──────────┼──────────────┼──────────────┼──────────────┘
      │          │              │              │
      ▼          ▼              ▼              ▼
  ┌────────┐ ┌────────┐  ┌──────────┐  ┌──────────┐
  │Weather │ │ Stock  │  │Calculator│  │Greeting  │
  │ :9002  │ │ :9003  │  │  :9004   │  │  :9005   │
  │🔒 OAuth│ │🔒 OAuth│  │🔓 Open   │  │🔑 OIDC   │
  └───┬────┘ └───┬────┘  └──────────┘  └────┬─────┘
      │          │                           │
      ▼          ▼                           ▼
  ┌──────────────────┐               ┌──────────────┐
  │  Keycloak :8180  │◄──────────────│ JWT Verify   │
  │  Token Introspect│               │ via JWKS     │
  └──────────────────┘               └──────────────┘
```

### Three Auth Strategies — Side by Side

This template demonstrates three authentication models you'll encounter in enterprise MCP deployments:

| Server | Auth | How it works | When to use |
|--------|------|-------------|-------------|
| **Calculator** (:9004) | `none` | No authentication. Anyone can call it. | Public tools, internal-only networks, dev/test |
| **Weather** (:9002) | `oauth` | Client sends an **access_token** from `client_credentials` grant. Server **introspects** it with Keycloak (RFC 7662). | Machine-to-machine. No user context needed. |
| **Stock** (:9003) | `oauth` | Same as weather. | Machine-to-machine. |
| **Greeting** (:9005) | `oidc` | Client sends an **id_token** from `password` grant (or `authorization_code`). Server **verifies the JWT** signature via Keycloak's JWKS endpoint. | User-identity-aware tools. Know *who* is calling. |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Auth Strategy Comparison                            │
├─────────────────────┬──────────────────────┬────────────────────────────┤
│   No Auth           │  OAuth (introspect)  │  OIDC (JWT/JWKS)          │
│                     │                      │                            │
│  Client ──► Server  │  Client ──► Keycloak │  Client ──► Keycloak      │
│  (no headers)       │    get access_token  │    get id_token            │
│                     │       │              │    (password / auth_code)  │
│                     │       ▼              │       │                    │
│                     │  Client ──► Server   │       ▼                   │
│                     │  Bearer: access_token│  Client ──► Server        │
│                     │       │              │  Bearer: id_token          │
│                     │       ▼              │       │                    │
│                     │  Server ──► Keycloak │       ▼                   │
│                     │  introspect token    │  Server verifies JWT      │
│                     │  (is it valid?)      │  locally via JWKS keys    │
│                     │                      │  (no Keycloak call)       │
└─────────────────────┴──────────────────────┴────────────────────────────┘
```

### Dual Connectivity — Gateway vs. Direct

Clients can reach MCP servers in two ways:

```
                          ┌──────────────────────────────────────────────┐
                          │              Clients                         │
                          │  ┌─────────────┐  ┌───────────┐  ┌───────┐ │
                          │  │  ADK+AGUI   │  │ LangGraph │  │  CLI  │ │
                          │  │  :8001      │  │  :8002    │  │ REPL  │ │
                          │  └──────┬──────┘  └─────┬─────┘  └───┬───┘ │
                          └─────────┼───────────────┼─────────────┼─────┘
                                    │               │             │
             ┌──────────────────────┼───────────────┼─────────────┼────┐
             │  Path A: Gateway     │               │             │    │
             │  (single endpoint)   ▼               ▼             ▼    │
             │             ┌──────────────────────────────────────────┐ │
             │             │        Gateway (port 8000)              │ │
             │             │  Routes to correct server by tool name  │ │
             │             └────────────────────┬────────────────────┘ │
             └──────────────────────────────────┼──────────────────────┘
                                                │
             ┌──── Path B: Direct connections ──┼──────────────────────┐
             │                                  │                      │
             │    ┌─────────┬─────────┬─────────┬──────────┐          │
             │    ▼         ▼         ▼         ▼          │          │
             │ ┌───────┐ ┌───────┐ ┌────────┐ ┌────────┐  │          │
             │ │Weather│ │ Stock │ │  Calc  │ │Greeting│  │          │
             │ │ :9002 │ │ :9003 │ │ :9004  │ │ :9005  │  │          │
             │ │🔒oauth│ │🔒oauth│ │🔓 open │ │🔑 oidc │  │          │
             │ └───────┘ └───────┘ └────────┘ └────────┘  │          │
             └─────────────────────────────────────────────┘          │
                                                                      │
                    ┌────────────────┐    ┌──────────────────────┐    │
                    │ Keycloak :8180 │    │  MCP Registry        │    │
                    │ OIDC Provider  │    │  Backend :8080       │    │
                    │ (dev IdP)      │    │  Frontend :3000      │    │
                    └────────────────┘    └──────────────────────┘    │
```

- **Path A — Gateway**: One URL for everything. The gateway discovers tools from all servers and routes requests. Best for production — centralizes auth, rate-limiting, and observability.
- **Path B — Direct**: Each server is called individually. Best for local development and per-server auth control. The ADK client uses this mode.

### Service Registry Data Flow

```
┌──────────────┐    ┌──────────────────────────────────────────────┐
│  Registry    │    │           Status Checker (every 60s)         │
│  Frontend    │    │                                              │
│  React :3000 │    │  For each registered server:                 │
│              │    │    1. Get auth token (oauth/oidc/none)       │
│   GET /api/  │    │    2. POST /mcp → initialize (JSON-RPC)     │
│   servers    │    │    3. POST /mcp → tools/list (JSON-RPC)     │
│              │    │    4. Parse SSE response → count tools       │
│      │       │    │    5. Update status + tools_count in DB      │
│      ▼       │    └──────────────────────────────────────────────┘
│  ┌────────┐  │                         │
│  │ Server │  │    ┌────────────────────┘
│  │ Cards  │  │    │
│  │ with   │◄─┼────┘
│  │ status │  │
│  └────────┘  │
└──────────────┘
```

---

## Quick Start (5 minutes)

> **Prerequisites**: Docker Desktop, Python 3.11+, Google Cloud CLI (`gcloud`)

```bash
# 1. Clone
git clone https://github.com/vishalgoswami/genai-mcps.git && cd mcps

# 2. Configure
cp .env.example .env
# Edit .env → set GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# 3. Authenticate with GCP (for Gemini / Vertex AI)
gcloud auth application-default login

# 4. Start the full stack
docker compose up -d

# 5. Open the chat UI
open http://localhost:8001
```

That's it. You now have 4 MCP servers, Keycloak, a registry, and a Gemini-powered chat client running locally.

---

## Detailed Setup Guide

### Prerequisites

| Tool | Install | What for |
|------|---------|----------|
| **Python 3.11+** | `brew install python@3.13` | MCP servers, clients |
| **Docker Desktop** | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) | Container orchestration |
| **Google Cloud CLI** | `brew install google-cloud-sdk` | Vertex AI / Gemini auth |
| **Node.js 20+** | `brew install node` | Registry frontend (dev only) |

### Step 1 — Clone and configure

```bash
git clone https://github.com/vishalgoswami/genai-mcps.git
cd mcps
cp .env.example .env
```

Edit `.env`:

```dotenv
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
MCP_AUTH_ENABLED=true    # "false" to skip OAuth entirely
```

### Step 2 — Authenticate with Google Cloud

The ADK chat client uses **Gemini** on Vertex AI via Application Default Credentials (ADC). No API keys — just:

```bash
gcloud auth application-default login
gcloud auth application-default print-access-token  # verify
```

### Step 3 — Start the identity provider (Keycloak)

Keycloak provides the local OAuth2/OIDC infrastructure. In production you'd use your corporate IdP — here it simulates that role.

```bash
docker compose up keycloak -d
```

Wait for healthy status (~30–45 seconds):

```bash
docker inspect --format '{{.State.Health.Status}}' mcps-keycloak-1
# → healthy
```

**What gets auto-configured**: The `mcp` realm, pre-loaded from `infra/keycloak/realm-export.json`, includes:

| Keycloak Client | Secret | Purpose |
|-----------------|--------|---------|
| `weather-server` | `weather-server-secret` | Weather MCP server (introspection) |
| `stock-server` | `stock-server-secret` | Stock MCP server (introspection) |
| `greeting-server` | `greeting-server-secret` | Greeting MCP server (JWKS) |
| `adk-agui-client` | `adk-agui-secret` | ADK chat client (gets tokens) |
| `mcp-gateway` | `gateway-secret` | Gateway (confidential) |
| `mcp-registry` | `registry-secret` | Registry status checker |

Test user: `testuser` / `testpass` (for OIDC password grant flows)

Admin console: http://localhost:8180 — login `admin` / `admin`

> **Why Keycloak?** It's self-contained (single Docker container), fully OIDC-compliant, and supports realm export/import so every developer gets identical config with zero manual setup. See [Swapping Identity Providers](#swapping-identity-providers-for-production) for production alternatives.

### Step 4 — Start MCP servers

```bash
# All 4 servers + Keycloak (if not already running)
docker compose up weather-server stock-server calculator-server greeting-server -d
```

Verify they're running:

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

**Or run locally** (for development with hot reload):

```bash
# Calculator (no auth, no shared lib needed)
cd servers/calculator
python -m venv .venv && source .venv/bin/activate
pip install -e .
calculator-server --transport streamable-http --port 9004

# Weather (OAuth — needs shared lib)
cd servers/weather
python -m venv .venv && source .venv/bin/activate
pip install -e . -e ../../shared/
MCP_AUTH_ENABLED=true KEYCLOAK_URL=http://localhost:8180 KEYCLOAK_REALM=mcp \
  OAUTH_CLIENT_ID=weather-server OAUTH_CLIENT_SECRET=weather-server-secret \
  weather-server --transport streamable-http --port 9002
```

### Step 5 — Verify OAuth is working

```bash
# Get an access_token (client_credentials grant):
TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=adk-agui-client \
  -d client_secret=adk-agui-secret | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Without token → 401:
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# → 401

# With token → 200:
curl -s -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# → {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26",...}}
```

**Test OIDC id_token flow** (for the greeting server):

```bash
# Get an id_token (password grant with openid scope):
ID_TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d grant_type=password \
  -d client_id=adk-agui-client \
  -d client_secret=adk-agui-secret \
  -d username=testuser \
  -d password=testpass \
  -d scope=openid | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# Call greeting server with id_token:
curl -s -X POST http://localhost:9005/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# → {"jsonrpc":"2.0","id":1,"result":{...,"serverInfo":{"name":"greeting",...}}}
```

### Step 6 — Start the ADK chat client

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

# Per-server auth — mix all three strategies:
MCP_SERVERS=[
  {"url":"http://localhost:9002/mcp","auth":"oauth"},
  {"url":"http://localhost:9003/mcp","auth":"oauth"},
  {"url":"http://localhost:9004/mcp"},
  {"url":"http://localhost:9005/mcp","auth":"oidc"}
]

KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=mcp
OAUTH_CLIENT_ID=adk-agui-client
OAUTH_CLIENT_SECRET=adk-agui-secret
OIDC_USERNAME=testuser
OIDC_PASSWORD=testpass
```

```bash
adk-agui
# → [adk-agui]   🔒 oauth  http://localhost:9002/mcp
# → [adk-agui]   🔒 oauth  http://localhost:9003/mcp
# → [adk-agui]   🔓 public http://localhost:9004/mcp
# → [adk-agui]   🔑 oidc   http://localhost:9005/mcp
# → Uvicorn running on http://0.0.0.0:8001
```

Open http://localhost:8001 — try asking:
- *"What's the weather in California?"*
- *"How is AAPL doing?"*
- *"What is 42 factorial?"*
- *"Say hello in Japanese"*

### Step 7 — Start the registry and gateway

```bash
docker compose up registry-backend registry-frontend gateway -d
```

- **Registry UI**: http://localhost:3000 — browse all MCP servers, their status, and tool counts
- **Registry API**: http://localhost:8080/api/servers/
- **Gateway**: http://localhost:8000/mcp — smart auth proxy, aggregates all tools, handles per-server auth

### Full stack (one command)

```bash
docker compose up -d
# Starts everything: Keycloak, 4 MCP servers, gateway, registry backend + frontend
```

---

## Components in Detail

### MCP Servers

| Server | Port | Auth | Tools | Description |
|--------|------|------|-------|-------------|
| **Weather** | 9002 | 🔒 OAuth (introspect) | `get_alerts`, `get_forecast` | US weather data from NWS API |
| **Stock** | 9003 | 🔒 OAuth (introspect) | `get_stock_price`, `get_stock_history`, `get_company_info` | Market data via yfinance |
| **Calculator** | 9004 | 🔓 None | `add`, `multiply`, `factorial` | Basic math — intentionally open |
| **Greeting** | 9005 | 🔑 OIDC (JWT/JWKS) | `greet`, `farewell` | Multi-language greetings — needs user identity |

All servers use **FastMCP** (`mcp.server.fastmcp.FastMCP`) with streamable-HTTP transport. Each supports three transports via `--transport`: `stdio` (local dev), `sse`, `streamable-http` (Docker/cloud).

### ADK Chat Client

The chat client uses **Google ADK** (Agent Development Kit) with **Gemini 2.5 Flash** on Vertex AI as the LLM. It:

1. Connects to all configured MCP servers via streamable-HTTP
2. Auto-discovers available tools from each server
3. Uses Gemini to route user questions to the appropriate tool(s)
4. Handles auth per-server: no-auth, `client_credentials`, or OIDC `password` grant

**Client auth config** (`MCP_SERVERS` JSON array):

```jsonc
[
  {"url": "http://localhost:9002/mcp", "auth": "oauth"},  // client_credentials → access_token
  {"url": "http://localhost:9003/mcp", "auth": "oauth"},  // client_credentials → access_token
  {"url": "http://localhost:9004/mcp"},                    // no auth
  {"url": "http://localhost:9005/mcp", "auth": "oidc"}    // password grant → id_token
]
```

### API Gateway

Aggregating reverse-proxy that unifies all MCP servers behind `http://gateway:8000/mcp`. Configured via `gateway/config/servers.yaml`.

### Service Registry

- **Backend** (FastAPI + SQLite): Stores server metadata, runs a background status checker every 60s that probes each server using MCP JSON-RPC protocol with the appropriate auth
- **Frontend** (React + Vite + Tailwind): Cards showing server name, status, tool count, auth type

### Keycloak (Local IdP)

A fully configured Keycloak instance that auto-imports the `mcp` realm on startup. Provides:

- OAuth2 token endpoint for `client_credentials` and `password` grants
- Token introspection endpoint (RFC 7662) for access token validation
- JWKS endpoint for JWT signature verification (OIDC id_tokens)
- Pre-configured clients for every component in the stack

---

## Keycloak Local IdP Setup

This section explains how the local Keycloak identity provider is configured and how to customize it.

### Realm Configuration

All auth configuration lives in `infra/keycloak/realm-export.json`. This file is auto-imported when the Keycloak container starts via the `--import-realm` flag.

The realm named `mcp` contains:

**Clients** (9 pre-configured):

| Client ID | Type | Service Account | Purpose |
|-----------|------|----------------|---------|
| `weather-server` | Confidential | Yes | Weather server introspection |
| `stock-server` | Confidential | Yes | Stock server introspection |
| `greeting-server` | Confidential | No | Greeting server (JWKS only) |
| `adk-agui-client` | Confidential | Yes | ADK chat client |
| `mcp-gateway` | Confidential | Yes | Gateway |
| `mcp-registry` | Confidential | Yes | Registry status checker |
| `cli-client` | Confidential | Yes | CLI REPL client |
| `langgraph-client` | Confidential | Yes | LangGraph client |
| `mcp-client` | Public | N/A | Browser-based clients |

**Users**:

| Username | Password | Purpose |
|----------|----------|---------|
| `testuser` | `testpass` | OIDC password grant for id_token flows |
| `admin` | `admin` | Keycloak admin console |

**Scopes**: `openid`, `profile`, `email` — assigned to all clients by default.

### How Docker Hostname Works

Keycloak runs inside Docker as `keycloak:8080` but is accessed externally at `http://localhost:8180`. This dual-identity is handled by:

```yaml
command: start-dev --import-realm --hostname http://localhost:8180 --hostname-backchannel-dynamic true
```

- `--hostname http://localhost:8180` — tokens contain `iss: http://localhost:8180/realms/mcp`
- `--hostname-backchannel-dynamic true` — allows internal services (reaching Keycloak as `keycloak:8080`) to validate tokens with the `localhost:8180` issuer claim

Without `--hostname-backchannel-dynamic true`, token introspection from inside Docker returns `active: false` because the issuer URL doesn't match.

### Adding a New Keycloak Client

**Option A — Realm export file** (recommended for reproducibility):

Add to the `clients` array in `infra/keycloak/realm-export.json`:

```json
{
  "clientId": "my-new-server",
  "enabled": true,
  "protocol": "openid-connect",
  "publicClient": false,
  "secret": "my-server-secret",
  "directAccessGrantsEnabled": true,
  "serviceAccountsEnabled": true,
  "standardFlowEnabled": true,
  "redirectUris": ["http://localhost:*"],
  "webOrigins": ["*"],
  "defaultClientScopes": ["openid", "profile", "email"]
}
```

Then restart Keycloak: `docker compose up keycloak -d --force-recreate`

**Option B — Admin UI** (for quick testing):

1. Open http://localhost:8180 → `admin` / `admin`
2. Select `mcp` realm → Clients → Create client
3. Client ID: `my-new-server`, Client authentication: ON
4. Credentials tab → copy the generated secret

### Token Flows Reference

**Client Credentials (for OAuth servers)**:

```bash
curl -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=adk-agui-client \
  -d client_secret=adk-agui-secret
# → {"access_token": "eyJ...", "token_type": "Bearer", "expires_in": 300}
```

**Password Grant with OpenID (for OIDC servers)**:

```bash
curl -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d grant_type=password \
  -d client_id=adk-agui-client \
  -d client_secret=adk-agui-secret \
  -d username=testuser \
  -d password=testpass \
  -d scope=openid
# → {"access_token": "eyJ...", "id_token": "eyJ...", "token_type": "Bearer"}
```

**Introspect a token** (what OAuth servers do internally):

```bash
curl -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token/introspect \
  -d token=eyJ... \
  -d client_id=weather-server \
  -d client_secret=weather-server-secret
# → {"active": true, "client_id": "adk-agui-client", "scope": "..."}
```

---

## Swapping Identity Providers for Production

Keycloak is the **development** IdP. In production, swap it for your organization's existing provider. The MCP auth layer is **IdP-agnostic** — it only requires standard OIDC endpoints.

### What the MCP servers need

| Auth Type | Required Endpoint | Standard |
|-----------|------------------|----------|
| `oauth` (introspection) | `/.well-known/openid-configuration` → `introspection_endpoint` | RFC 7662 |
| `oidc` (JWT/JWKS) | `/.well-known/openid-configuration` → `jwks_uri` | OpenID Connect |

### Compatible Identity Providers

| IdP | Grant Types | Notes |
|-----|------------|-------|
| **Auth0** | All | Managed OIDC, built-in introspection |
| **Okta** | All | Enterprise SSO, introspection via `/oauth2/v1/introspect` |
| **Azure AD (Entra ID)** | `client_credentials`, `authorization_code` | Microsoft ecosystem |
| **Google Cloud Identity** | `authorization_code`, service accounts | If already on GCP |
| **AWS Cognito** | All | If hosting MCP servers on AWS |
| **PingIdentity / ForgeRock** | All | Enterprise on-prem alternatives |

### How to swap

Update environment variables on each MCP server:

```dotenv
KEYCLOAK_URL=https://your-idp.example.com     # OIDC provider base URL
KEYCLOAK_REALM=your-tenant                     # realm / tenant / directory
OAUTH_CLIENT_ID=my-server                      # confidential client
OAUTH_CLIENT_SECRET=...                        # client secret
```

The `KeycloakTokenVerifier` and `OIDCIdTokenVerifier` in `shared/mcp_utils/oauth_middleware.py` discover endpoints automatically via `/.well-known/openid-configuration`, so they work with any compliant provider despite the "Keycloak" name.

---

## Enterprise Deployment — Beyond Local Docker

This template runs everything on `localhost` for learning. In a real enterprise, the deployment looks very different.

### Production Architecture on GCP

```
                    ┌────────────────────────────────────┐
                    │          Corporate IdP              │
                    │  (Okta / Azure AD / Auth0)          │
                    └────────────┬───────────────────────┘
                                 │
        ┌────────────────────────┼──────────────────────────────┐
        │                   GCP Project                         │
        │                                                       │
        │  ┌─────────────┐   ╔══════════════════════════════╗  │
        │  │  Cloud Run   │   ║     GKE Cluster              ║  │
        │  │  or App      │   ║                              ║  │
        │  │  Engine      │   ║  ┌────────┐  ┌────────┐     ║  │
        │  │              │   ║  │Weather │  │ Stock  │     ║  │
        │  │ ┌──────────┐ │   ║  │  Pod   │  │  Pod   │     ║  │
        │  │ │ ADK Chat │ │   ║  └────────┘  └────────┘     ║  │
        │  │ │ Client   │ │   ║  ┌────────┐  ┌────────┐     ║  │
        │  │ └──────────┘ │   ║  │  Calc  │  │Greeting│     ║  │
        │  │ ┌──────────┐ │   ║  │  Pod   │  │  Pod   │     ║  │
        │  │ │ Registry │ │   ║  └────────┘  └────────┘     ║  │
        │  │ │ Backend  │ │   ║                              ║  │
        │  │ └──────────┘ │   ║  ┌──────────────────────┐    ║  │
        │  └─────────────┘    ║  │ Gateway (Ingress)    │    ║  │
        │                     ║  └──────────────────────┘    ║  │
        │                     ╚══════════════════════════════╝  │
        │                                                       │
        │  ┌─────────────────┐   ┌──────────────────────────┐  │
        │  │  Cloud SQL      │   │  Vertex AI (Gemini)      │  │
        │  │  (Registry DB)  │   │  LLM for ADK agent       │  │
        │  └─────────────────┘   └──────────────────────────┘  │
        │                                                       │
        │  ┌─────────────────┐   ┌──────────────────────────┐  │
        │  │  Secret Manager │   │  Cloud CDN / LB          │  │
        │  │  (OAuth creds)  │   │  (Registry frontend)     │  │
        │  └─────────────────┘   └──────────────────────────┘  │
        └───────────────────────────────────────────────────────┘
```

### What changes in production

| Concern | Local (this template) | Production (GCP) |
|---------|----------------------|-------------------|
| **MCP Servers** | Docker containers on localhost | GKE pods or Cloud Run services |
| **Identity Provider** | Keycloak in Docker | Corporate IdP (Okta, Azure AD, Google IAM) |
| **Secrets** | `.env` files, realm-export.json | Google Secret Manager |
| **Database** | SQLite file | Cloud SQL (PostgreSQL) |
| **Client App** | Local Python process | Cloud Run or App Engine |
| **Registry Frontend** | Nginx in Docker | Cloud CDN + Cloud Storage |
| **Networking** | `localhost` ports | Internal VPC, Cloud Load Balancer |
| **TLS** | None (HTTP) | Managed TLS via Google-managed certs |
| **Discovery** | Hard-coded URLs or env vars | Service mesh (Istio/Anthos), DNS |
| **Scaling** | Single instance | Horizontal Pod Autoscaler / Cloud Run auto-scale |
| **Monitoring** | Docker logs | Cloud Logging, Cloud Monitoring, OpenTelemetry |

### Key considerations for enterprise MCP

1. **Service mesh for discovery**: Instead of hard-coded server URLs, use Kubernetes service DNS (`weather-server.mcp.svc.cluster.local`) or Istio for automatic mTLS between services.

2. **Workload Identity**: Replace `OAUTH_CLIENT_SECRET` env vars with GKE Workload Identity — pods authenticate to the IdP via bound service account tokens, no secrets to manage.

3. **API Gateway / Ingress**: Use Apigee, Cloud Endpoints, or an Istio ingress gateway instead of the custom FastAPI gateway. These add rate-limiting, API key management, and analytics.

4. **Network policies**: MCP servers on GKE should have Kubernetes NetworkPolicies restricting which namespaces/pods can reach them.

5. **Multi-tenancy**: In a platform team model, different teams own different MCP servers. The registry becomes critical for discoverability, and OAuth scopes/roles control which clients can access which servers.

---

## Adding a New MCP Server

### 1. Create the server

```bash
mkdir -p servers/my-server/src && touch servers/my-server/src/__init__.py
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
p.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "9006")))
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

### 2. Add it to the client

In `clients/adk-agui/.env`, add to the `MCP_SERVERS` array:

```json
{"url": "http://localhost:9006/mcp", "auth": "oauth"}
```

### 3. (Optional) Register in Keycloak

Add a client entry to `infra/keycloak/realm-export.json` (see [Keycloak section](#adding-a-new-keycloak-client)).

### 4. (Optional) Add to Docker Compose

```yaml
  my-server:
    build:
      context: .
      dockerfile: servers/my-server/Dockerfile
    ports:
      - "9006:9006"
    environment:
      MCP_AUTH_ENABLED: ${MCP_AUTH_ENABLED:-false}
      KEYCLOAK_URL: http://keycloak:8080
      OAUTH_CLIENT_ID: my-server
      OAUTH_CLIENT_SECRET: my-server-secret
    depends_on:
      keycloak:
        condition: service_healthy
```

---

## Repository Structure

```
mcps/
├── servers/
│   ├── weather/          # 🔒 OAuth — US weather alerts & forecasts (port 9002)
│   ├── stock/            # 🔒 OAuth — Stock prices & company info (port 9003)
│   ├── calculator/       # 🔓 Open  — Basic math operations (port 9004)
│   ├── greeting/         # 🔑 OIDC  — Multi-language greetings (port 9005)
│   └── Dockerfile.template
├── gateway/              # API gateway — single MCP endpoint (port 8000)
├── clients/
│   ├── adk-agui/         # Google ADK + Gemini chat client (port 8001)
│   ├── cli/              # Terminal REPL client
│   └── langgraph/        # LangGraph agent client (port 8002)
├── registry/
│   ├── backend/          # FastAPI registry API (port 8080)
│   └── frontend/         # React registry UI (port 3000)
├── shared/               # mcp_utils — OAuth verifiers, base classes, types
├── infra/
│   ├── keycloak/         # Realm config (realm-export.json)
│   └── credentials.yaml  # Credentials template (never commit real secrets)
├── docker-compose.yml    # Full stack orchestration
└── .env.example          # Environment template
```

## Port Assignments

| Component | Port | Auth |
|-----------|------|------|
| Gateway | 8000 | — |
| ADK+AGUI Client | 8001 | — |
| LangGraph Client | 8002 | — |
| Registry Backend | 8080 | — |
| Registry Frontend | 3000 | — |
| Keycloak | 8180 | — |
| Weather Server | 9002 | 🔒 OAuth |
| Stock Server | 9003 | 🔒 OAuth |
| Calculator Server | 9004 | 🔓 None |
| Greeting Server | 9005 | 🔑 OIDC |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVERS` | — | JSON array of `{url, auth}` server configs |
| `MCP_AUTH_ENABLED` | `false` | Enable OAuth on MCP servers |
| `KEYCLOAK_URL` | `http://localhost:8180` | Keycloak base URL |
| `KEYCLOAK_REALM` | `mcp` | Keycloak realm |
| `OAUTH_CLIENT_ID` | varies | OAuth client ID |
| `OAUTH_CLIENT_SECRET` | varies | OAuth client secret |
| `OIDC_USERNAME` | `testuser` | User for OIDC password grant |
| `OIDC_PASSWORD` | `testpass` | Password for OIDC password grant |
| `MCP_TRANSPORT` | `stdio` / `streamable-http` | MCP transport protocol |
| `LLM_MODEL` | `gemini-2.5-flash` | Gemini model for ADK agent |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project ID |
| `GOOGLE_GENAI_USE_VERTEXAI` | — | Set `true` for Vertex AI |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 Authentication required` | Missing or expired Bearer token | Get a fresh token (see Step 5) |
| Token introspection returns `active: false` | Keycloak hostname mismatch in Docker | Ensure `--hostname http://localhost:8180 --hostname-backchannel-dynamic true` in Keycloak command |
| OIDC id_token rejected by greeting server | Issuer mismatch | The `OIDCIdTokenVerifier` auto-discovers the canonical issuer from Keycloak's OIDC config — ensure Keycloak is reachable from the server container |
| `Connection refused` | Service not running | `docker ps` to check; `docker compose up <service> -d` |
| Keycloak stuck starting | Slow Docker or low memory | Wait 60s; check `docker logs mcps-keycloak-1` |
| `ModuleNotFoundError: mcp_utils` | Shared lib not installed | `pip install -e ../../shared/` in the server's venv |
| Registry shows `unknown` status | Status checker hasn't run yet | Wait 60 seconds for the first check cycle |
| Calculator returns 404 | Wrong URL | Calculator has no auth — hit `http://localhost:9004/mcp` directly |

---

## Changelog

### v0.6.0 — Gateway Smart Auth Proxy

- **Gateway redesign**: Rewrote the MCP gateway as a smart auth proxy that aggregates tools from all 4 upstream servers (11 tools) into a single MCP endpoint at `:8000/mcp`
- **Per-server auth handling**: Gateway manages upstream auth automatically — `client_credentials` for OAuth servers (weather, stock), id_token pass-through for OIDC servers (greeting), no auth for open servers (calculator)
- **Low-level MCP Server**: Gateway uses `mcp.server.Server` (not `FastMCP`) with `StreamableHTTPSessionManager` for raw argument passthrough — avoids Pydantic schema validation on proxy calls, preserves upstream `inputSchema` exactly
- **Tool namespacing**: Upstream tools exposed as `{server}__{tool}` (e.g., `weather__get_forecast`)
- **ASGI token middleware**: `_TokenExtractMiddleware` extracts client Bearer token into `ContextVar` for OIDC pass-through
- **Token caching**: OAuth access tokens cached with ~4.5 min TTL to avoid per-request Keycloak calls
- **`servers.yaml` auth_type**: Config uses `auth_type: none|oauth|oidc` per server (replaces old `auth: true/false`)
- **`fetch_oidc_id_token`**: New helper in `shared/mcp_utils/credentials.py` — password grant with `scope=openid` → returns `id_token`
- **Gateway README**: Comprehensive design docs with auth flow diagrams, configuration reference, testing examples

### v0.5.0 — Multi-Auth MCP Servers + OIDC Id-Token Support

- **Calculator server** (port 9004): New open MCP server with no authentication — 3 tools: `add`, `multiply`, `factorial`
- **Greeting server** (port 9005): New OIDC-protected MCP server — validates `id_token` JWT via Keycloak's JWKS endpoint (no introspection), 2 tools: `greet`, `farewell` in 10 languages
- **`OIDCIdTokenVerifier`**: New token verifier in `shared/mcp_utils/oauth_middleware.py` — verifies JWT signature via JWKS, auto-discovers canonical issuer from OIDC discovery (handles Docker hostname mismatch)
- **Three auth strategies**: `none` (open), `oauth` (client_credentials + introspection), `oidc` (id_token + JWT/JWKS) — demonstrated across the 4 servers
- **ADK client OIDC support**: `auth` field now accepts `"oidc"` — fetches id_token via password grant with `scope=openid`, sends as Bearer token
- **Registry multi-auth probing**: Status checker handles all three auth types when probing servers
- **Keycloak `greeting-server` client**: Added to `realm-export.json`
- **Enterprise README**: Complete rewrite with progressive detail, DFD diagrams, Keycloak local IdP guide, production GCP architecture, auth strategy comparison

### v0.4.0 — MCP Registry with Docker Deploy & OAuth-Aware Status Checker

- **Registry Docker deployment**: Backend (python:3.12-slim) and frontend (node+nginx multi-stage) Dockerfiles added to docker-compose
- **MCP JSON-RPC status checker**: Rewrote status checker to use proper MCP protocol — sends `initialize` then `tools/list` JSON-RPC messages instead of ad-hoc HTTP
- **OAuth token exchange**: Registry backend fetches Bearer tokens from Keycloak via `client_credentials` grant to probe OAuth-protected MCP servers
- **SSE response parsing**: Status checker handles both SSE (`event: message\ndata: {...}`) and plain JSON responses from MCP servers
- **Seed data on startup**: Weather and stock MCP servers auto-registered in the registry with correct Docker-internal URLs and `auth_type=oauth`
- **`mcp-registry` Keycloak client**: New confidential client added to `realm-export.json` with service account enabled
- **Frontend build config**: Added `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, and `vite-env.d.ts`

### v0.3.0 — Pluggable Client Config & Architecture Docs

- **Per-server OAuth control**: `MCPServerConfig` dataclass — each MCP server independently enables/disables OAuth via `MCP_SERVERS` JSON
- **Dual connectivity model**: Gateway (single endpoint) or direct (per-server URLs)
- **IdP-agnostic design**: Any OIDC-compliant provider works via standard RFC 7662 introspection

### v0.2.0 — Native OAuth via FastMCP + Keycloak

- **FastMCP native auth**: `AuthSettings` + `KeycloakTokenVerifier` (MCP SDK's `TokenVerifier` protocol)
- **RFC 7662 token introspection**: Works with all grant types including `client_credentials`
- **Keycloak hostname fix**: `--hostname-backchannel-dynamic true` resolves Docker hostname mismatch

### v0.1.0 — Multi-Transport MCP Servers + ADK Client

- **Weather & Stock MCP servers**: FastMCP with `stdio`, `sse`, `streamable-http` transport
- **Google ADK + AG-UI client**: Gemini-powered chat UI, auto-discovers tools via `MCPToolset`
- **Docker deployment**: Server Dockerfiles, hatchling builds, Docker Compose orchestration

### v0.0.1 — Initial Commit

- Monorepo scaffold and build configuration

---

## License

MIT
