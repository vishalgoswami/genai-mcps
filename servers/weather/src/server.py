"""
Weather MCP Server — supports stdio, SSE, and streamable HTTP transports.

Exposes two tools via MCP:
  - get_alerts(state)    → active weather alerts for a US state
  - get_forecast(lat, lon) → 5-period weather forecast for a location

Usage:
  weather-server              # stdio (default, for local/dev use)
  weather-server --transport sse
  weather-server --transport streamable-http
  weather-server --transport streamable-http --host 0.0.0.0 --port 9002

Reference: https://modelcontextprotocol.io/docs/develop/build-server
Data source: US National Weather Service API (https://api.weather.gov)
"""
from typing import Any
import argparse
import os
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings

# ── Parse CLI args early so host/port can be passed to FastMCP ───────────────
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Weather MCP Server")
    p.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (default: stdio, or MCP_TRANSPORT env var)",
    )
    p.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"), help="Bind host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "9002")), help="Bind port (default: 9002)")
    return p.parse_args()

_args = _parse_args()

# ── OAuth configuration (optional, gated by MCP_AUTH_ENABLED) ────────────────
_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"
_KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
_KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
_OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "weather-server")
_OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "weather-server-secret")


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
        print(f"[weather] OAuth ENABLED — issuer: {issuer_url}")
    return FastMCP("weather", **kwargs)


mcp = _build_mcp()

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


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    transport = _args.transport
    print(f"[weather] Starting with transport={transport}, host={_args.host}, port={_args.port}")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
