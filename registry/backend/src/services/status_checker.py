"""Background task that polls registered MCP servers and updates their status."""
from __future__ import annotations
import os
from datetime import datetime, timezone
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src import models

_scheduler = AsyncIOScheduler()
INTERVAL = int(os.getenv("STATUS_CHECK_INTERVAL", "60"))


async def _check_all():
    db: Session = SessionLocal()
    try:
        servers = db.query(models.MCPServer).all()
        for server in servers:
            status, tools_count = await _probe(server.url)
            server.status = status
            server.tools_count = tools_count
            server.last_checked = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


async def _probe(url: str) -> tuple[str, int]:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{url}/tools")
            resp.raise_for_status()
            tools = resp.json().get("tools", [])
            return "online", len(tools)
    except Exception:
        return "offline", 0


def start_status_checker(app):
    _scheduler.add_job(_check_all, "interval", seconds=INTERVAL, id="status_checker")
    _scheduler.start()
    app.state.scheduler = _scheduler
