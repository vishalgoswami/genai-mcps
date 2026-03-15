"""
Weather MCP Server — streamable HTTP transport with optional OAuth (Keycloak).

Exposes two tools via MCP:
  - get_alerts(state)    → active weather alerts for a US state
  - get_forecast(lat, lon) → 5-period weather forecast for a location

Reference: https://modelcontextprotocol.io/docs/develop/build-server
Data source: US National Weather Service API (https://api.weather.gov)
"""
from typing import Any
import os
import httpx
from mcp.server.fastmcp import FastMCP

# ── FastMCP instance ─────────────────────────────────────────────────────────
mcp = FastMCP("weather")

# ── Constants ────────────────────────────────────────────────────────────────
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "mcp-weather-server/1.0"


# ── Helpers ──────────────────────────────────────────────────────────────────
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return (
        f"Event: {props.get('event', 'Unknown')}\n"
        f"Area: {props.get('areaDesc', 'Unknown')}\n"
        f"Severity: {props.get('severity', 'Unknown')}\n"
        f"Status: {props.get('status', 'Unknown')}\n"
        f"Headline: {props.get('headline', 'N/A')}\n"
        f"Description: {props.get('description', 'No description available')}\n"
        f"Instructions: {props.get('instruction', 'No specific instructions provided')}"
    )


# ── Tools ────────────────────────────────────────────────────────────────────
@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = (
            f"{period['name']}:\n"
            f"  Temperature: {period['temperature']}°{period['temperatureUnit']}\n"
            f"  Wind: {period['windSpeed']} {period['windDirection']}\n"
            f"  Forecast: {period['detailedForecast']}"
        )
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


# ── Entry point — streamable HTTP with optional OAuth ─────────────────────────
def main():
    MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"

    if MCP_AUTH_ENABLED:
        # Wrap FastMCP's ASGI app with OAuth middleware
        import sys
        # Add shared lib to path so we can import oauth_middleware
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))
        from mcp_utils.oauth_middleware import OAuthMiddleware
        from starlette.middleware import Middleware

        print("[weather] OAuth enabled — tokens validated against Keycloak")
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=9002,
            middleware=[Middleware(OAuthMiddleware)],
        )
    else:
        print("[weather] OAuth disabled — open access")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=9002)


if __name__ == "__main__":
    main()
