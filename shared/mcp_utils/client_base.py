"""Base MCP client — thin HTTP wrapper for any MCP server."""
from __future__ import annotations
import httpx
from mcp_utils.types import ToolDef, ToolCallResult


class BaseMCPClient:
    def __init__(self, server_url: str, timeout: float = 30.0):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout

    def list_tools(self) -> list[ToolDef]:
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.get(f"{self.server_url}/tools")
            resp.raise_for_status()
            return [ToolDef(**t) for t in resp.json().get("tools", [])]

    def call_tool(self, tool_name: str, **kwargs) -> ToolCallResult:
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.post(f"{self.server_url}/call/{tool_name}", json=kwargs)
            resp.raise_for_status()
            return ToolCallResult(tool=tool_name, output=resp.json())

    async def acall_tool(self, tool_name: str, **kwargs) -> ToolCallResult:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            resp = await c.post(f"{self.server_url}/call/{tool_name}", json=kwargs)
            resp.raise_for_status()
            return ToolCallResult(tool=tool_name, output=resp.json())
