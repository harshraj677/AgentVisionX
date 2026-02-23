"""AgentVision X — FastAPI Backend Server (v2)."""
import asyncio
from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from models import QueryRequest
from websocket_manager import manager
from execution_engine import engine
from logger import get_execution_history

app = FastAPI(title="AgentVision X", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Must keep strong references to background tasks to prevent GC ──
_background_tasks: set = set()


def _run_task(coro):
    """Create a task and prevent garbage collection until it finishes."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


@app.get("/")
async def root():
    return {"name": "AgentVision X", "version": "2.0.0", "status": "running"}


@app.post("/api/execute")
async def execute_query(request: QueryRequest):
    """Start agent execution for a query (triggers WebSocket updates)."""
    _run_task(engine.execute(request.query, model=request.model))
    return {"status": "started", "query": request.query, "model": request.model}


@app.post("/api/execute-with-failure")
async def execute_with_failure(request: QueryRequest):
    """Execute with a simulated failure at the given step."""
    failure_step_id = request.step_id
    _run_task(engine.execute(request.query, failure_step_id=failure_step_id, model=request.model))
    return {"status": "started", "query": request.query, "failure_step": failure_step_id}


@app.post("/api/rerun-step/{step_id}")
async def rerun_step(step_id: str):
    """Re-run a specific step."""
    _run_task(engine.rerun_step(step_id))
    return {"status": "rerunning", "step_id": step_id}


@app.post("/api/cancel")
async def cancel_execution():
    """Cancel current execution."""
    engine.cancel()
    return {"status": "cancelled"}


@app.get("/api/history")
async def get_history(limit: int = 50):
    """Get execution history."""
    return get_execution_history(limit)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
