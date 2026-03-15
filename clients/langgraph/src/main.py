"""LangGraph MCP client — entry point."""
import uvicorn
from fastapi import FastAPI
from src.graph.graph import build_graph
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="MCP LangGraph Client", version="0.1.0")
graph = build_graph()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(body: dict):
    user_message = body.get("message", "")
    thread_id = body.get("thread_id", "default")
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke({"messages": [("human", user_message)]}, config=config)
    last_msg = result["messages"][-1]
    return {"response": last_msg.content}


def run():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    run()
