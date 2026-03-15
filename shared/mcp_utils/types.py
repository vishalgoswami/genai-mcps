"""Shared Pydantic types used across servers and clients."""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class ToolDef(BaseModel):
    """Describes a single MCP tool."""
    name: str
    description: str = ""
    input_schema: dict = {}


class ToolCallResult(BaseModel):
    """Result returned by a tool call."""
    tool: str
    output: Any
    error: Optional[str] = None
    is_error: bool = False
