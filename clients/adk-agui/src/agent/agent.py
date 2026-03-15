"""
Google ADK supervisor agent with multi-server MCP tool integration.

Connects to one or many remote MCP servers via streamable HTTP,
discovers all available tools, and acts as a supervisor agent that
can route user queries to the right tools across any configured server.

Configure servers via comma-separated MCP_SERVER_URLS env var:
  MCP_SERVER_URLS=http://localhost:9002/mcp,http://localhost:9003/mcp
"""
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
import os


# Comma-separated list of MCP server URLs
MCP_SERVER_URLS = os.getenv(
    "MCP_SERVER_URLS",
    os.getenv("MCP_SERVER_URL", "http://localhost:9002/mcp"),
)
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "vg-pp-001")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")


def _parse_server_urls(urls_str: str) -> list[str]:
    """Parse comma-separated MCP server URLs into a list."""
    return [u.strip() for u in urls_str.split(",") if u.strip()]


def build_agent() -> LlmAgent:
    """
    Create an ADK supervisor agent with tools auto-discovered from
    all configured MCP servers (streamable HTTP).

    Each MCP server URL gets its own MCPToolset — the agent sees the
    union of all tools and can route queries to any of them.
    """
    server_urls = _parse_server_urls(MCP_SERVER_URLS)

    # Create one MCPToolset per server
    mcp_toolsets = [
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(url=url),
        )
        for url in server_urls
    ]

    server_list = "\n".join(f"  - {url}" for url in server_urls)
    print(f"[adk-agui] Connecting to {len(server_urls)} MCP server(s):\n{server_list}")

    agent = LlmAgent(
        name="mcp_supervisor",
        model=LLM_MODEL,
        description="A supervisor agent that routes queries across multiple MCP servers.",
        instruction=(
            "You are a helpful supervisor assistant connected to multiple MCP tool servers. "
            "You have access to tools from different domains (weather, stock prices, etc.). "
            "Analyze the user's question and use the most appropriate tool(s) to answer. "
            "If a question spans multiple domains, call tools from different servers as needed. "
            "Always explain what you are doing before calling a tool. "
            "If no tool is relevant, answer from your own knowledge and say so."
        ),
        tools=mcp_toolsets,
    )
    return agent
