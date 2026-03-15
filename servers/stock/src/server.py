"""
Stock Price MCP Server — streamable HTTP transport with optional OAuth (Keycloak).

Exposes tools via MCP:
  - get_stock_price(symbol)          → current quote for a ticker symbol
  - get_stock_history(symbol, days)  → recent daily closing prices
  - get_company_info(symbol)         → basic company profile

Data source: Yahoo Finance via the yfinance library (no API key required).
"""
from __future__ import annotations

import os
from typing import Any

import yfinance as yf
from mcp.server.fastmcp import FastMCP

# ── FastMCP instance ─────────────────────────────────────────────────────────
mcp = FastMCP("stock")


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


# ── Entry point — streamable HTTP with optional OAuth ─────────────────────────
def main():
    MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"

    if MCP_AUTH_ENABLED:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))
        from mcp_utils.oauth_middleware import OAuthMiddleware
        from starlette.middleware import Middleware

        print("[stock] OAuth enabled — tokens validated against Keycloak")
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=9003,
            middleware=[Middleware(OAuthMiddleware)],
        )
    else:
        print("[stock] OAuth disabled — open access")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=9003)


if __name__ == "__main__":
    main()
