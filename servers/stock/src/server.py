"""
Stock Price MCP Server — supports stdio, SSE, and streamable HTTP transports.

Exposes tools via MCP:
  - get_stock_price(symbol)          → current quote for a ticker symbol
  - get_stock_history(symbol, days)  → recent daily closing prices
  - get_company_info(symbol)         → basic company profile

Usage:
  stock-server              # stdio (default, for local/dev use)
  stock-server --transport sse
  stock-server --transport streamable-http
  stock-server --transport streamable-http --host 0.0.0.0 --port 9003

Data source: Yahoo Finance via the yfinance library (no API key required).
"""
from __future__ import annotations

import argparse
import os
from typing import Any

import yfinance as yf
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings

# ── Parse CLI args early so host/port can be passed to FastMCP ───────────────
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stock Price MCP Server")
    p.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (default: stdio, or MCP_TRANSPORT env var)",
    )
    p.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"), help="Bind host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "9003")), help="Bind port (default: 9003)")
    return p.parse_args()

_args = _parse_args()

# ── OAuth configuration (optional, gated by MCP_AUTH_ENABLED) ────────────────
_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"
_KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
_KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
_OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "stock-server")
_OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "stock-server-secret")


def _build_mcp() -> FastMCP:
    """Build FastMCP instance, with native OAuth when enabled."""
    kwargs: dict[str, Any] = dict(host=_args.host, port=_args.port)
    if _AUTH_ENABLED:
        from mcp_utils.oauth_middleware import KeycloakTokenVerifier
        issuer_url = f"{_KEYCLOAK_URL}/realms/{_KEYCLOAK_REALM}"
        resource_url = f"http://localhost:{_args.port}"
        kwargs["auth"] = AuthSettings(
            issuer_url=issuer_url,
            resource_server_url=resource_url,
        )
        kwargs["token_verifier"] = KeycloakTokenVerifier(
            keycloak_url=_KEYCLOAK_URL,
            realm=_KEYCLOAK_REALM,
            client_id=_OAUTH_CLIENT_ID,
            client_secret=_OAUTH_CLIENT_SECRET,
        )
        print(f"[stock] OAuth ENABLED — issuer: {issuer_url}")
    return FastMCP("stock", **kwargs)


mcp = _build_mcp()


# ── Helpers ──────────────────────────────────────────────────────────────────
def _safe_get(data: dict, key: str, default: str = "N/A") -> Any:
    return data.get(key, default) or default


# ── Tools ────────────────────────────────────────────────────────────────────
@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    """Get the current stock price and key metrics for a ticker symbol.

    Args:
        symbol: Stock ticker symbol (e.g. AAPL, GOOGL, MSFT)
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.fast_info

        price = getattr(info, "last_price", None)
        prev_close = getattr(info, "previous_close", None)
        market_cap = getattr(info, "market_cap", None)
        day_high = getattr(info, "day_high", None)
        day_low = getattr(info, "day_low", None)

        if price is None:
            return f"Unable to fetch price for '{symbol}'. Verify the ticker symbol is correct."

        change = (price - prev_close) if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0

        market_cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"

        return (
            f"Symbol: {symbol.upper()}\n"
            f"Price: ${price:,.2f}\n"
            f"Change: {change:+,.2f} ({change_pct:+,.2f}%)\n"
            f"Day Range: ${day_low:,.2f} - ${day_high:,.2f}\n"
            f"Previous Close: ${prev_close:,.2f}\n"
            f"Market Cap: {market_cap_str}"
        )
    except Exception as e:
        return f"Error fetching stock price for '{symbol}': {e}"


@mcp.tool()
async def get_stock_history(symbol: str, days: int = 30) -> str:
    """Get recent daily closing prices for a stock.

    Args:
        symbol: Stock ticker symbol (e.g. AAPL, GOOGL, MSFT)
        days: Number of days of history to retrieve (default: 30, max: 365)
    """
    try:
        days = min(max(days, 1), 365)
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=f"{days}d")

        if hist.empty:
            return f"No history found for '{symbol}'. Verify the ticker symbol."

        lines = [f"Stock History — {symbol.upper()} (last {len(hist)} trading days)"]
        lines.append("-" * 50)
        for date, row in hist.tail(20).iterrows():  # Show at most last 20 rows
            date_str = date.strftime("%Y-%m-%d")
            lines.append(
                f"{date_str}  Close: ${row['Close']:,.2f}  "
                f"Volume: {int(row['Volume']):,}"
            )

        if len(hist) > 20:
            lines.append(f"... showing last 20 of {len(hist)} days")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching history for '{symbol}': {e}"


@mcp.tool()
async def get_company_info(symbol: str) -> str:
    """Get basic company information for a stock ticker.

    Args:
        symbol: Stock ticker symbol (e.g. AAPL, GOOGL, MSFT)
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        if not info or "shortName" not in info:
            return f"No company information found for '{symbol}'."

        return (
            f"Company: {_safe_get(info, 'shortName')}\n"
            f"Sector: {_safe_get(info, 'sector')}\n"
            f"Industry: {_safe_get(info, 'industry')}\n"
            f"Country: {_safe_get(info, 'country')}\n"
            f"Employees: {_safe_get(info, 'fullTimeEmployees')}\n"
            f"Website: {_safe_get(info, 'website')}\n"
            f"Summary: {_safe_get(info, 'longBusinessSummary', 'No summary available.')[:500]}"
        )
    except Exception as e:
        return f"Error fetching company info for '{symbol}': {e}"


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    transport = _args.transport
    print(f"[stock] Starting with transport={transport}, host={_args.host}, port={_args.port}")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
