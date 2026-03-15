# Keycloak OIDC Setup for MCP Servers

This directory holds the Keycloak realm configuration that's auto-imported on container startup.

## What's configured

| Item | Value |
|---|---|
| Realm | `mcp` |
| Confidential client | `mcp-server` (secret: `changeme`) — used by MCP servers |
| Public client | `mcp-client` — used by CLI/agent clients |
| Test user | `testuser` / `testpass` |

## Endpoints (local)

| Endpoint | URL |
|---|---|
| Keycloak Admin Console | http://localhost:8180/admin (admin/admin) |
| OIDC Discovery | http://localhost:8180/realms/mcp/.well-known/openid-configuration |
| Token endpoint | http://localhost:8180/realms/mcp/protocol/openid-connect/token |

## Getting a token (password grant, for testing)

```bash
curl -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=mcp-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "scope=openid"
```

## Getting a token (client_credentials grant)

```bash
curl -X POST http://localhost:8180/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=mcp-server" \
  -d "client_secret=changeme"
```
