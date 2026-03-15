"""Optional API-key auth middleware for the gateway."""
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
import os

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")


async def verify_api_key(request: Request, call_next):
    """Simple API-key guard. Skip if GATEWAY_API_KEY is not set."""
    if GATEWAY_API_KEY:
        key = request.headers.get("X-API-Key")
        if key != GATEWAY_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return await call_next(request)
