# MCP Gateway

A reverse-proxy / aggregator that exposes a single endpoint and routes MCP tool calls to the appropriate upstream server.

## Running

```bash
pip install -e .
gateway
# or
uvicorn src.main:app --reload
```

## Config

Edit `config/servers.yaml` to register MCP servers.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/mcp/servers` | List registered servers |
| POST | `/mcp/call/{server}/{tool}` | Proxy a tool call |
