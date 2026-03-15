# clients/adk-agui

Conversational agentic web app built on [Google ADK](https://google.github.io/adk-docs/) + [AG-UI](https://docs.agui.dev/).  
Connects to any MCP server and exposes chat via a streaming REST API.

## Running

```bash
pip install -e .
cp ../../.env.example .env   # fill in GOOGLE_API_KEY, MCP_SERVER_URL
adk-agui
# open http://localhost:8001
```

## Key files

| File | Description |
|---|---|
| `src/agent/agent.py` | ADK `LlmAgent` definition |
| `src/agent/tools.py` | Discovers & wraps MCP tools for ADK |
| `src/ui/app.py` | FastAPI + AG-UI streaming server |
