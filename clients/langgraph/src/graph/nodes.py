"""Graph node implementations."""
from __future__ import annotations
from langchain_core.messages import AIMessage, SystemMessage
from src.graph.state import AgentState
from src.mcp.adapters import get_mcp_tools
import os


def make_llm_node(llm, system_prompt: str = ""):
    """Returns a node that calls the LLM with bound MCP tools and an optional system prompt."""
    tools = get_mcp_tools()
    llm_with_tools = llm.bind_tools(tools)

    async def llm_node(state: AgentState) -> dict:
        messages = list(state.messages)
        # Inject system prompt if provided and not already present
        if system_prompt and (not messages or not isinstance(messages[0], SystemMessage)):
            messages.insert(0, SystemMessage(content=system_prompt))
        response: AIMessage = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return llm_node


def make_tool_node():
    """Returns a node that executes tool calls returned by the LLM."""
    from langgraph.prebuilt import ToolNode
    tools = get_mcp_tools()
    return ToolNode(tools)
