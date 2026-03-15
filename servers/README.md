# Servers

Each subdirectory is a standalone MCP server served via **streamable HTTP** transport, deployable to a local Docker container.

All servers optionally integrate with **Keycloak** for OAuth2/OIDC authentication (set `MCP_AUTH_ENABLED=true`).

| Server | Port | Description | Status |
|---|---|---|---|
| weather | 9002 | US weather alerts & forecasts (NWS API) | ready |
| test-mcp-server | — | Minimal test/reference server | placeholder |

## Adding a New Server

1. `cp -r weather my-new-server`
2. Update `pyproject.toml` name and dependencies
3. Implement tools inside `src/server.py` using `FastMCP`
4. Copy `Dockerfile.template` → `my-new-server/Dockerfile`, adjust paths & port
5. Add entry to `docker-compose.yml` and `../gateway/config/servers.yaml`
6. Register in the MCP Registry via the web UI
