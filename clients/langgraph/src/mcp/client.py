"""
MCP client — connects to MCP servers via streamable HTTP, with LangChain tool adapters.

Supports server_label for namespacing tools from multiple servers.
"""
from __future__ import annotations
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_core.tools import StructuredTool
from pydantic import create_model, Field
from typing import Any


class MCPClient:
    """Discovers MCP tools and wraps them as LangChain StructuredTools."""

    def __init__(self, server_url: str, server_label: str | None = None):
        self.server_url = server_url
        self.server_label = server_label

    def list_tools_as_langchain(self) -> list[StructuredTool]:
        """Synchronously discover MCP tools and return LangChain wrappers."""
        return asyncio.run(self._alist_tools())

    async def _alist_tools(self) -> list[StructuredTool]:
        async with streamablehttp_client(self.server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return [self._wrap(t) for t in result.tools]

    def _wrap(self, tool) -> StructuredTool:
        """Wrap a single MCP tool definition as a LangChain StructuredTool."""
        server_url = self.server_url
        original_name = tool.name
        # Use server label prefix if provided to avoid name collisions
        name = f"{self.server_label}__{original_name}" if self.server_label else original_name
        description = tool.description or ""
        if self.server_label:
            description = f"[{self.server_label}] {description}"
        input_schema = tool.inputSchema or {"type": "object", "properties": {}}

        # Build a Pydantic model from the JSON Schema for structured args
        fields = {}
        props = input_schema.get("properties", {})
        required = set(input_schema.get("required", []))
        for k, v in props.items():
            py_type = _json_type_to_python(v.get("type", "string"))
            default = ... if k in required else None
            fields[k] = (py_type, Field(default=default, description=v.get("description", "")))

        ArgsModel = create_model(f"{name}_args", **fields) if fields else None

        async def _invoke(**kwargs) -> str:
            async with streamablehttp_client(server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(original_name, arguments=kwargs)
                    return result.content[0].text if result.content else "(empty)"

        return StructuredTool(
            name=name,
            description=description,
            coroutine=_invoke,
            func=lambda **kw: asyncio.run(_invoke(**kw)),
            args_schema=ArgsModel,
        )


def _json_type_to_python(json_type: str) -> type:
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, Any)
