"""Registry backend — FastAPI application entry point."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import engine, Base, SessionLocal
from src.routers import servers, health
from src.services.status_checker import start_status_checker
from src import models
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080

    class Config:
        env_prefix = "REGISTRY_"


settings = Settings()

Base.metadata.create_all(bind=engine)

# ── Default MCP servers to seed on first run ─────────────────────────────────
_DEFAULT_SERVERS = [
    {
        "name": "weather",
        "description": "US weather alerts & forecasts (NWS API)",
        "url": "http://weather-server:9002/mcp",
        "tags": "weather,nws,alerts,forecasts",
        "owner": "platform",
        "auth_type": "oauth",
    },
    {
        "name": "stock",
        "description": "Stock prices, history & company info",
        "url": "http://stock-server:9003/mcp",
        "tags": "stock,finance,market",
        "owner": "platform",
        "auth_type": "oauth",
    },
]


def _seed_default_servers():
    """Insert default MCP servers if they don't already exist."""
    db = SessionLocal()
    try:
        for entry in _DEFAULT_SERVERS:
            exists = db.query(models.MCPServer).filter(
                models.MCPServer.name == entry["name"]
            ).first()
            if not exists:
                db.add(models.MCPServer(**entry))
        db.commit()
    finally:
        db.close()


_seed_default_servers()

app = FastAPI(
    title="MCP Registry",
    description="Web-based registry for remote MCP servers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(servers.router, prefix="/api")


@app.on_event("startup")
async def startup():
    start_status_checker(app)


def run():
    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)


if __name__ == "__main__":
    run()
