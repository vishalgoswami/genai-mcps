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
- **Auth via ADC**: Client apps (adk-agui, langgraph) use Google Cloud Application Default Credentials — never API keys. Set `GOOGLE_GENAI_USE_VERTEXAI=true` in `.env`.
- **OAuth (optional)**: MCP servers can require Keycloak Bearer tokens via `MCP_AUTH_ENABLED=true`. The `OAuthMiddleware` in `shared/mcp_utils/` handles validation.
- **Hatchling builds**: All Python packages use hatchling. Source lives in `src/`, so every `pyproject.toml` needs `[tool.hatch.build.targets.wheel] packages = ["src"]` (or `["mcp_utils"]` for shared).
- **Docker context**: Server Dockerfiles use the repo root as build context (to COPY `shared/`). Use `docker build -f servers/<name>/Dockerfile .` from root.

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
```

## Conventions

- MCP server entry points are registered as `[project.scripts]` in pyproject.toml
- Server names in docker-compose match gateway `config/servers.yaml`
- Credentials template is in `infra/credentials.yaml` — never commit real secrets
- `.env` is gitignored; copy from `.env.example`
