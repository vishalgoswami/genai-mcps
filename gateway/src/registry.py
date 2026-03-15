"""Server registry — loads and manages known MCP servers from config."""
from __future__ import annotations
import yaml
from typing import Dict, Optional


class ServerRegistry:
    def __init__(self, config_path: str):
        self._config_path = config_path
        self._servers: Dict[str, dict] = {}

    async def load(self):
        with open(self._config_path) as f:
            data = yaml.safe_load(f)
        self._servers = {s["name"]: s for s in data.get("servers", [])}
        print(f"[registry] Loaded {len(self._servers)} server(s)")

    def get(self, name: str) -> Optional[dict]:
        return self._servers.get(name)

    def all(self) -> list:
        return list(self._servers.values())
