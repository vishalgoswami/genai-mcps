"""Registry backend — FastAPI application entry point."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import engine, Base
from src.routers import servers, health
from src.services.status_checker import start_status_checker
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
