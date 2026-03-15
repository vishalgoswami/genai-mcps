# Weather MCP Server

An MCP server exposing US weather alerts and forecasts from the [National Weather Service API](https://api.weather.gov).

Based on the [official MCP build-server tutorial](https://modelcontextprotocol.io/docs/develop/build-server).

## Tools

| Tool | Args | Description |
|---|---|---|
| `get_alerts` | `state` (2-letter code, e.g. CA) | Active weather alerts for a US state |
| `get_forecast` | `latitude`, `longitude` | 5-period forecast for a lat/lon |

## Running locally

```bash
pip install -e .
weather-server
# → Streamable HTTP on http://0.0.0.0:9002/mcp
```

## Running with Docker

```bash
docker build -t mcp-weather .
docker run -p 9002:9002 mcp-weather
```

## Testing

```bash
# List tools
curl http://localhost:9002/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Call get_alerts
curl http://localhost:9002/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_alerts","arguments":{"state":"CA"}}}'
```
