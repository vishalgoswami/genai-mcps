"""Base MCP server — FastAPI helper that wires tools to standard endpoints."""
from __future__ import annotations
from fastapi import FastAPI
from mcp_utils.types import ToolDef
from typing import Callable


class BaseMCPServer:
    """Inherit from this to build a FastAPI-based MCP server quickly."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._tools: dict[str, tuple[ToolDef, Callable]] = {}
        self.app = FastAPI(title=name, description=description)
        self._register_routes()

    def tool(self, name: str, description: str = "", input_schema: dict = {}):
        """Decorator to register a function as an MCP tool."""
        def decorator(fn: Callable):
            self._tools[name] = (ToolDef(name=name, description=description, input_schema=input_schema), fn)
            return fn
        return decorator

    def _register_routes(self):
        @self.app.get("/tools")
        def list_tools():
            return {"tools": [td.model_dump() for td, _ in self._tools.values()]}

        @self.app.post("/call/{tool_name}")
        async def call_tool(tool_name: str, payload: dict = {}):
            if tool_name not in self._tools:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            _, fn = self._tools[tool_name]
            result = await fn(**payload) if callable(fn) else fn(**payload)
            return {"result": result}

        @self.app.get("/health")
        def health():
            return {"status": "ok", "server": self.name}
