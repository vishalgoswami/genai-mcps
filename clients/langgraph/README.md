# clients/langgraph

LangGraph-based conversational ReAct agent connected to any MCP server.

## Running

```bash
pip install -e .
cp ../../.env.example .env   # fill in OPENAI_API_KEY, MCP_SERVER_URL
langgraph-mcp
# POST http://localhost:8002/chat  {"message": "...", "thread_id": "abc"}
```

## Architecture

```
User → /chat → LangGraph graph
                  ├── llm node  (ChatOpenAI with MCP tools bound)
                  ├── tools node (ToolNode → calls MCP server)
                  └── MemorySaver checkpointer (per-thread history)
```

## Key files

| File | Description |
|---|---|
| `src/graph/graph.py` | Graph wiring — ReAct loop |
| `src/graph/nodes.py` | LLM and tool executor nodes |
| `src/graph/state.py` | `AgentState` schema |
| `src/mcp/client.py` | HTTP client for MCP server |
| `src/mcp/adapters.py` | MCP tools → LangChain tools |
