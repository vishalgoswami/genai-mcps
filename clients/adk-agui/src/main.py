"""Entry point — starts the AG-UI FastAPI server backed by the ADK agent."""
import uvicorn
from fastapi import FastAPI
from src.ui.app import build_agui_app
from dotenv import load_dotenv

load_dotenv()

app: FastAPI = build_agui_app()


def run():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    run()
