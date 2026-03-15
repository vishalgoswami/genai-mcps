"""
LangGraph state graph — supervisor-style ReAct agent with Gemini.

Discovers tools from all configured MCP servers and routes queries
to the appropriate tools across any domain.
"""
from __future__ import annotations
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, SystemMessage
from src.graph.state import AgentState
from src.graph.nodes import make_llm_node, make_tool_node
import os

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "vg-pp-001")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

SUPERVISOR_PROMPT = (
    "You are a supervisor assistant connected to multiple MCP tool servers. "
    "You have access to tools from various domains (weather, stock market, etc.). "
    "Analyze the user's question and decide which tool(s) to call. "
    "If a question spans multiple domains, call tools from different servers as needed. "
    "Always explain your reasoning before calling a tool. "
    "If no tool is relevant, answer from your own knowledge and say so."
)


def _should_continue(state: AgentState) -> str:
    last: AIMessage = state.messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_graph():
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        project=GOOGLE_CLOUD_PROJECT,
        streaming=True,
    )

    graph = StateGraph(AgentState)
    graph.add_node("llm", make_llm_node(llm, system_prompt=SUPERVISOR_PROMPT))
    graph.add_node("tools", make_tool_node())

    graph.set_entry_point("llm")
    graph.add_conditional_edges("llm", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "llm")

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
