# MCPs — Model Context Protocol Hub

A monorepo containing MCP server implementations, client applications, a gateway, and a web-based MCP registry.

## Structure

```
mcps/
├── servers/          # MCP server implementations
├── gateway/          # MCP gateway (aggregates & proxies multiple servers)
├── clients/          # MCP client applications
│   ├── adk-agui/     # Google ADK + AG-UI conversational agent
│   ├── cli/          # Terminal-based MCP CLI client
│   └── langgraph/    # LangGraph conversational agent
├── registry/         # Web-based MCP server registry app
│   ├── backend/      # FastAPI backend
│   └── frontend/     # React frontend
└── shared/           # Shared Python utilities
```

## Quick Start

```bash
cp .env.example .env
# then cd into any component and follow its README
```
