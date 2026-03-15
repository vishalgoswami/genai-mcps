"""AG-UI FastAPI application — serves chat UI and streams ADK agent responses."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.agent.agent import build_agent

STATIC_DIR = Path(__file__).parent / "static"


def build_agui_app() -> FastAPI:
    app = FastAPI(title="MCP ADK+AGUI Client", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    agent = build_agent()
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service, app_name="mcp_agui", auto_create_session=True)

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/chat")
    async def chat(body: dict):
        """Non-streaming chat endpoint. Returns the agent's final text response."""
        user_message = body.get("message", "")
        session_id = body.get("session_id", "default")

        new_message = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )

        final_text = ""
        async for event in runner.run_async(
            user_id="user",
            session_id=session_id,
            new_message=new_message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text += part.text

        return {"response": final_text or "No response from agent."}

    return app
