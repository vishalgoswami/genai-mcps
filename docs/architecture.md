# Architecture

## Overview

```
┌──────────────────────────────────────────────────────────┐
│                        Clients                           │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │ adk-agui   │  │    CLI     │  │   LangGraph      │   │
│  │ (port 8001)│  │ (terminal) │  │   (port 8002)    │   │
│  └─────┬──────┘  └─────┬──────┘  └────────┬─────────┘   │
└────────┼───────────────┼──────────────────┼─────────────┘
         │               │                  │
         └───────────────▼──────────────────┘
                         │
              ┌──────────▼──────────┐
              │      Gateway        │
              │    (port 8000)      │
              └──────────┬──────────┘
                         │  routes by server name
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
  │ MCP Server  │ │ MCP Server  │ │ MCP Server  │
  │  (port 9001)│ │  (port 9002)│ │  (port 9003)│
  └─────────────┘ └─────────────┘ └─────────────┘

              ┌──────────────────────┐
              │    MCP Registry      │
              │  Backend (port 8080) │
              │  Frontend (port 3000)│
              └──────────────────────┘
```

## Components

| Component | Port | Tech |
|---|---|---|
| Gateway | 8000 | FastAPI |
| ADK+AGUI Client | 8001 | FastAPI + Google ADK + AG-UI |
| LangGraph Client | 8002 | FastAPI + LangGraph |
| Registry Backend | 8080 | FastAPI + SQLite |
| Registry Frontend | 3000 | React + Vite + Tailwind |
| MCP Servers | 9001+ | FastAPI (via BaseMCPServer) |
