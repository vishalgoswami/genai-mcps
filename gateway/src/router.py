"""
Legacy REST router — kept for backward compatibility.
The gateway now primarily exposes an MCP endpoint via FastMCP.
This module provides a REST fallback for non-MCP clients.
"""
from fastapi import APIRouter, HTTPException
import httpx


def router() -> APIRouter:
    r = APIRouter(prefix="/api")

    @r.get("/health")
    async def health():
        return {"status": "ok", "mode": "mcp-proxy"}

    return r
