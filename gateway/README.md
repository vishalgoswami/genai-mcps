# MCP Gateway — Smart Auth Proxy

A single MCP endpoint that aggregates tools from all upstream MCP servers and
handles per-server authentication automatically. Clients talk to one endpoint;
the gateway manages all upstream auth.

## Design

### Problem

Without a gateway, every client must:

1. Know each MCP server's URL independently
2. Manage different auth strategies per server (OAuth `client_credentials`,
   OIDC `id_token`, or no auth)
3. Maintain separate token caches, client secrets, and credential flows
4. Discover tools from each server separately

### Solution

The gateway acts as a **smart auth proxy** that sits between clients and
upstream MCP servers:

```
┌────────┐                    ┌────────────────────┐
│ Client │ ── OIDC id_token ─►│   MCP Gateway      │
│        │◄── aggregated ──── │   :8000/mcp         │
│        │    tools           │                    │
└────────┘                    │  ┌──────────────┐  │
                              │  │ Token Cache   │  │
                              │  └──────┬───────┘  │
                              └─────────┼──────────┘
                                        │
                   ┌────────────────────┼────────────────────┐
                   │                    │                     │
              OAuth token          OIDC pass-through      No auth
              (client_creds)       (client's id_token)
                   │                    │                     │
            ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
            │ Weather 🔒  │      │ Greeting 🔑 │      │Calculator 🔓│
            │ Stock   🔒  │      └─────────────┘      └─────────────┘
            └─────────────┘
```

### Auth Strategy Per Server

The gateway supports three auth types, configured in `config/servers.yaml`:

| Auth Type | Upstream Header | How |
|---|---|---|
| `none` | *(empty)* | No auth — request forwarded as-is |
| `oauth` | `Bearer <access_token>` | Gateway fetches its own `client_credentials` token from Keycloak |
| `oidc` | `Bearer <id_token>` | Gateway passes through the client's OIDC id_token |

**OAuth servers** (weather, stock): The gateway has its own `OAUTH_CLIENT_ID` /
`OAUTH_CLIENT_SECRET` registered in Keycloak. It performs the
`client_credentials` grant to get an access token, caches it, and attaches it to
upstream requests. Clients don't need to know about these credentials.

**OIDC servers** (greeting): The client sends its own `id_token` as
`Authorization: Bearer <id_token>` to the gateway. The gateway extracts this
token and passes it through to the upstream server unchanged. The upstream
server validates the JWT signature via Keycloak's JWKS endpoint.

**Open servers** (calculator): No auth headers are sent upstream.

### Tool Aggregation

At startup, the gateway connects to every upstream server, discovering their
tools. Each tool is exposed with a namespaced name: `{server}__{tool}`.

For example, the `get_forecast` tool on the `weather` server becomes
`weather__get_forecast` at the gateway. The upstream tool's `inputSchema` is
preserved exactly — the gateway does not re-validate arguments, it passes them
through as-is.

The gateway also exposes a built-in `list_upstream_servers` tool that lists all
connected servers and their auth types.

### Architecture Details

- **Low-level MCP Server**: Uses `mcp.server.Server` (not `FastMCP`) for raw
  argument passthrough — avoids Pydantic schema validation on proxy calls
- **StreamableHTTPSessionManager**: Creates the MCP streamable-HTTP transport
- **ASGI middleware**: `_TokenExtractMiddleware` extracts the client's Bearer
  token from the `Authorization` header and stores it in a `ContextVar`,
  making it available to tool handlers for OIDC pass-through
- **Token caching**: OAuth access tokens are cached with a ~4.5 min TTL
  (tokens expire at 5 min) to avoid per-request Keycloak calls
- **Discovery auth**: At startup, the gateway uses its own credentials for all
  server types (including OIDC servers via password grant) to perform tool
  discovery

## Running

### Local (requires upstream servers running)

```bash
cd gateway
pip install -e .

# Set required env vars
export KEYCLOAK_URL=http://localhost:8180
export KEYCLOAK_REALM=mcp
export OAUTH_CLIENT_ID=mcp-gateway
export OAUTH_CLIENT_SECRET=gateway-secret
export OIDC_USERNAME=testuser
export OIDC_PASSWORD=testpass

gateway
```

### Docker (recommended — via docker-compose)

```bash
# From repo root
docker compose up
```

The gateway starts on port `8000` and discovers all upstream servers
automatically.

## Configuration

### `config/servers.yaml`

```yaml
servers:
  - name: weather
    url: http://weather-server:9002/mcp
    auth_type: oauth
    description: US weather alerts and forecasts via NWS API

  - name: stock
    url: http://stock-server:9003/mcp
    auth_type: oauth
    description: Stock prices, history, and company info

  - name: calculator
    url: http://calculator-server:9004/mcp
    auth_type: none
    description: Basic math operations

  - name: greeting
    url: http://greeting-server:9005/mcp
    auth_type: oidc
    description: Greetings and farewells (OIDC-protected)
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_PORT` | `8000` | Port the gateway listens on |
| `GATEWAY_SERVERS_CONFIG` | `../config/servers.yaml` | Path to servers YAML |
| `KEYCLOAK_URL` | `http://localhost:8180` | Keycloak base URL |
| `KEYCLOAK_REALM` | `mcp` | Keycloak realm name |
| `OAUTH_CLIENT_ID` | `mcp-gateway` | Client ID for OAuth token fetch |
| `OAUTH_CLIENT_SECRET` | `gateway-secret` | Client secret for OAuth token fetch |
| `OIDC_USERNAME` | — | Username for OIDC discovery token |
| `OIDC_PASSWORD` | — | Password for OIDC discovery token |

## Testing

```bash
# Initialize (via curl, must accept both content types)
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{
    "protocolVersion":"2025-03-26","capabilities":{},
    "clientInfo":{"name":"test","version":"1.0"}},"id":1}'

# List tools (11 tools from 4 servers + 1 meta-tool)
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id-from-init>" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}'

# Call a no-auth tool (calculator)
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id>" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{
    "name":"calculator__factorial","arguments":{"n":10}},"id":3}'

# Call an OIDC tool (greeting) — pass your id_token
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <your-id-token>" \
  -H "Mcp-Session-Id: <session-id>" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{
    "name":"greeting__greet","arguments":{"name":"World"}},"id":4}'
```
