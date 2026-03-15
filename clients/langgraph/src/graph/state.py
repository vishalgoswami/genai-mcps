"""Conversation state schema for the LangGraph agent."""
from __future__ import annotations
from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class AgentState(BaseModel):
    """State passed between graph nodes."""
    messages: Annotated[Sequence[BaseMessage], add_messages] = []
