"""
Calculator MCP Server — a simple, open (no auth) MCP server.

Exposes tools via MCP:
  - add(a, b)          → sum of two numbers
  - multiply(a, b)     → product of two numbers
  - factorial(n)       → factorial of n

Usage:
  calculator-server
  calculator-server --transport streamable-http --host 0.0.0.0 --port 9004

This server intentionally has NO authentication — demonstrating an open MCP endpoint.
"""
from __future__ import annotations

import argparse
import math
import os

from mcp.server.fastmcp import FastMCP


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Calculator MCP Server")
    p.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
    )
    p.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "9004")))
    return p.parse_args()


_args = _parse_args()

mcp = FastMCP("calculator", host=_args.host, port=_args.port)


@mcp.tool()
async def add(a: float, b: float) -> str:
    """Add two numbers.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    return f"{a} + {b} = {result}"


@mcp.tool()
async def multiply(a: float, b: float) -> str:
    """Multiply two numbers.

    Args:
        a: First number
        b: Second number
    """
    result = a * b
    return f"{a} × {b} = {result}"


@mcp.tool()
async def factorial(n: int) -> str:
    """Compute the factorial of a non-negative integer.

    Args:
        n: A non-negative integer (max 170 to avoid overflow)
    """
    if n < 0:
        return "Error: factorial is not defined for negative numbers."
    if n > 170:
        return "Error: n too large (max 170)."
    result = math.factorial(n)
    return f"{n}! = {result}"


def main():
    transport = _args.transport
    print(f"[calculator] Starting with transport={transport}, host={_args.host}, port={_args.port}")
    print("[calculator] Auth: NONE (open server)")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
