"""MCP tool integration for ADK.

Tools are now auto-discovered via MCPToolset in agent.py using native
MCP SDK streamable-HTTP transport. This module is kept for any future
custom tool wrappers.
"""
from __future__ import annotations

# ADK's MCPToolset handles tool discovery & execution natively.
# See src/agent/agent.py for the integration point.
