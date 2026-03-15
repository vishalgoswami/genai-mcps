"""AG-UI FastAPI application — streams ADK agent responses over SSE."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ag_ui.encoder import EventEncoder
from src.agent.agent import build_agent


def build_agui_app() -> FastAPI:
    app = FastAPI(title="MCP ADK+AGUI Client", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    agent = build_agent()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/chat")
    async def chat(body: dict):
        """Non-streaming chat endpoint. Returns the agent's final text response."""
        user_message = body.get("message", "")
        session_id = body.get("session_id", "default")
        result = await agent.run_async(user_id="user", session_id=session_id, message=user_message)
        return {"response": str(result)}

    return app
