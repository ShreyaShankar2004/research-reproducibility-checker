"""
FastAPI app: Multi-Agent Research Reproducibility Checker
"""
import os
import json
import sqlite3
import hashlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.orchestrator import run_pipeline
from app.agents.paper_ingestion import extract_arxiv_id, is_arxiv_query

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cache.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            cache_key TEXT PRIMARY KEY,
            result_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_cached(cache_key: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT result_json FROM reports WHERE cache_key = ?", (cache_key,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def set_cached(cache_key: str, result: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO reports (cache_key, result_json) VALUES (?, ?)",
        (cache_key, json.dumps(result)),
    )
    conn.commit()
    conn.close()


def query_to_cache_key(query: str) -> str:
    """arXiv queries cache by arXiv ID; other URLs cache by URL hash."""
    if is_arxiv_query(query):
        return extract_arxiv_id(query)
    return "ext_" + hashlib.sha256(query.encode()).hexdigest()[:16]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Multi-Agent Research Reproducibility Checker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://research-reproducibility-checker.vercel.app"],  # restrict in production to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    query: str  # arXiv URL/ID, or direct PDF URL
    force_refresh: bool = False


@app.get("/")
async def root():
    return {"status": "ok", "service": "repro-checker-api"}


@app.get("/api/cached/{cache_key}")
async def get_cached_report(cache_key: str):
    result = get_cached(cache_key)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return result


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """Non-streaming analysis endpoint (use WebSocket /ws/analyze for progress updates).
    Accepts an arXiv URL/ID or a direct PDF URL."""
    cache_key = query_to_cache_key(req.query)

    if not req.force_refresh:
        cached = get_cached(cache_key)
        if cached:
            cached["_cached"] = True
            return cached

    try:
        result = await run_pipeline(query=req.query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    set_cached(cache_key, result)
    result["_cached"] = False
    return result


@app.post("/api/analyze/upload")
async def analyze_upload(file: UploadFile = File(...)):
    """Analyze an uploaded PDF (for papers not available via URL/arXiv)."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()
    cache_key = "upload_" + hashlib.sha256(pdf_bytes).hexdigest()[:16]

    cached = get_cached(cache_key)
    if cached:
        cached["_cached"] = True
        return cached

    try:
        result = await run_pipeline(pdf_bytes=pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    set_cached(cache_key, result)
    result["_cached"] = False
    return result


@app.websocket("/ws/analyze")
async def analyze_ws(websocket: WebSocket):
    """Streaming analysis with progress updates. Accepts an arXiv URL/ID or direct PDF URL."""
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data.get("query", "")
        force_refresh = data.get("force_refresh", False)

        if not query:
            await websocket.send_json({"type": "error", "message": "No query provided."})
            await websocket.close()
            return

        cache_key = query_to_cache_key(query)

        if not force_refresh:
            cached = get_cached(cache_key)
            if cached:
                await websocket.send_json({"type": "progress", "message": "Found cached result."})
                cached["_cached"] = True
                await websocket.send_json({"type": "result", "data": cached})
                await websocket.close()
                return

        async def progress_callback(stage: str):
            await websocket.send_json({"type": "progress", "message": stage})

        try:
            result = await run_pipeline(query=query, progress_callback=progress_callback)
            set_cached(cache_key, result)
            result["_cached"] = False
            await websocket.send_json({"type": "result", "data": result})
        except ValueError as e:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception as e:
            await websocket.send_json({"type": "error", "message": f"Pipeline error: {str(e)}"})

        await websocket.close()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.close()
        except Exception:
            pass
