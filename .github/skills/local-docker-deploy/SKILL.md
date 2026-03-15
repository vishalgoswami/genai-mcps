---
name: "local-docker-deploy"
description: "Deploy MCP servers to local Docker with Keycloak OAuth. Build Docker images, start Keycloak OIDC, run MCP servers with streamable-http transport, configure OAuth tokens, test authenticated MCP endpoints, docker compose orchestration."
---

# Local Docker Deployment with Keycloak OAuth

Deploy MCP servers as Docker containers with optional Keycloak-based OAuth2 authentication.

## When to Use

- Deploying MCP servers to local Docker
- Setting up Keycloak OAuth for MCP server authentication
- Testing MCP endpoints with Bearer tokens
- Running the full stack via docker compose
- Debugging OAuth middleware or token validation issues

## Prerequisites

- Docker Desktop running
- Repo cloned at workspace root
- `.env` file created from template (gitignored)

## Procedure

### 1. Start Keycloak (OIDC Provider)

```bash
docker compose up -d keycloak
```

Wait for healthy status (~30s). Keycloak auto-imports the realm from `infra/keycloak/realm-export.json`.

| Item               | Value                                        |
|---------------------|----------------------------------------------|
| Admin console       | http://localhost:8180/admin (admin/admin)     |
| OIDC discovery      | http://localhost:8180/realms/mcp/.well-known/openid-configuration |
| Token endpoint      | http://localhost:8180/realms/mcp/protocol/openid-connect/token |
| Realm               | `mcp`                                        |
| Confidential client | `mcp-server` (secret: `changeme`)            |
| Public client       | `mcp-client`                                 |
| Test user           | `testuser` / `testpass`                      |

### 2. Build MCP Server Docker Images

All Dockerfiles use the repo root as build context (to COPY `shared/`):

```bash
# From repo root
docker build -f servers/weather/Dockerfile -t mcp-weather .
docker build -f servers/stock/Dockerfile -t mcp-stock .
```

Key Dockerfile conventions:
- Base image: `python:3.12-slim`
- Installs `shared/` first, then the server package
- Uses `pip install --no-cache-dir` (NOT `-e` — editable installs fail in Docker)
- Sets `ENV MCP_TRANSPORT=streamable-http`, `MCP_HOST=0.0.0.0`, `MCP_PORT=<port>`

### 3. Run MCP Servers Without OAuth

```bash
docker run -d --name weather -p 9002:9002 mcp-weather
docker run -d --name stock -p 9003:9003 mcp-stock
```

Test the endpoints:

```bash
# Initialize session
curl -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'

# List tools
curl -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: <session-id-from-above>" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'
```

### 4. Run MCP Servers With OAuth Enabled

Set `MCP_AUTH_ENABLED=true` in `.env` then run via docker compose:

```bash
# .env
MCP_AUTH_ENABLED=true

# Start everything
docker compose up -d
```

Or run individually with environment variables:

```bash
docker run -d --name weather -p 9002:9002 \
  -e MCP_AUTH_ENABLED=true \
  -e KEYCLOAK_URL=http://host.docker.internal:8180 \
  -e KEYCLOAK_REALM=mcp \
  mcp-weather
```

### 5. Obtain an OAuth Token

**Password grant (test user):**

```bash
TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=mcp-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "scope=openid" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**Client credentials grant:**

```bash
TOKEN=$(curl -s -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=mcp-server" \
  -d "client_secret=changeme" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 6. Test Authenticated MCP Endpoint

```bash
curl -X POST http://localhost:9002/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
```

Without a valid token, the `OAuthMiddleware` returns `401 Unauthorized`.

### 7. Full Stack via Docker Compose

```bash
# All services: keycloak, weather-server, stock-server, gateway, registry
docker compose up -d

# Check health
docker compose ps
```

Port assignments:
- Keycloak: 8180
- Weather server: 9002
- Stock server: 9003
- Gateway: 8000
- Registry backend: 8080
- Registry frontend: 3000

### 8. Adding a New MCP Server

1. Create `servers/<name>/src/server.py` using the multi-transport pattern (argparse + env vars)
2. Create `servers/<name>/pyproject.toml` with hatchling build and `packages = ["src"]`
3. Create `servers/<name>/Dockerfile` copying from `servers/Dockerfile.template`
4. Add the service to `docker-compose.yml` with health check
5. Add credentials to `infra/credentials.yaml`
6. Register in `gateway/config/servers.yaml`

## Troubleshooting

- **"Unable to determine which files to ship"** during Docker build → Add `[tool.hatch.build.targets.wheel] packages = ["src"]` to pyproject.toml
- **`FastMCP.run() got unexpected keyword argument 'host'`** → Pass host/port to `FastMCP()` constructor, not `run()`
- **401 on /mcp with valid token** → Check `KEYCLOAK_URL` is reachable from inside the container (use `http://keycloak:8080` in Docker network, `http://host.docker.internal:8180` for standalone containers)
- **Connection refused on 9002** → Ensure `MCP_HOST=0.0.0.0` (not 127.0.0.1) in Docker
