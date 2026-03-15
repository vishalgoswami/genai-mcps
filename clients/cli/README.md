# clients/cli

Terminal-based MCP client with an interactive REPL.

## Install

```bash
pip install -e .
```

## Usage

```bash
# Check server connectivity
mcp-cli connect http://localhost:9001

# List available tools
mcp-cli tools http://localhost:9001

# Start interactive chat
mcp-cli chat http://localhost:9001 --model gpt-4o
```
