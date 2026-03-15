# Calculator MCP Server

A simple, **open** (no authentication) MCP server that exposes basic math tools.

## Tools

| Tool | Description |
|------|-------------|
| `add(a, b)` | Sum of two numbers |
| `multiply(a, b)` | Product of two numbers |
| `factorial(n)` | Factorial of a non-negative integer |

## Run

```bash
# Local
cd servers/calculator && pip install -e . && calculator-server --transport streamable-http

# Docker (from repo root)
docker build -f servers/calculator/Dockerfile -t mcp-calculator .
docker run -p 9004:9004 mcp-calculator
```

## Port

Default: **9004**

## Auth

**None** — this server is intentionally open to demonstrate a public MCP endpoint.
