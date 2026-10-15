"""Loopback workbench API. The durable worker is a separate process."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .contracts import CampaignSpec, ReviewInput, AnnotationInput, ROLE_PROMPTS
from .engine import Engine, preflight
from .exporting import export_bundle, review, annotate
from .knowledge import Knowledge
from .providers import Provider
from .store import Store, uid
from .templates import catalog


class SourceInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=1_000_000)
    license: str = Field(min_length=1, max_length=200)
    source_url: str = Field(default="", max_length=2000)


def create_app(root: Path, store_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="Apertus Research Workbench", version="3.0.0")
    store = Store(store_root or Path(os.environ.get("WORKBENCH_DATA", root / "experiments/runs/workbench-v3")))
    engine = Engine(store)
    knowledge = Knowledge(Path(os.environ.get("WORKBENCH_WIKI", root / "experiments/wiki-workspace")))
    app.state.store, app.state.engine = store, engine

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse({"detail": "Cross-origin writes rejected"}, status_code=403)
            if "application/json" not in request.headers.get("content-type", ""):
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse({"detail": "JSON required"}, status_code=415)
            if int(request.headers.get("content-length", "0")) > 1_100_000:
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse({"detail": "Request too large"}, status_code=413)
            raw = await request.body()
            if len(raw) > 1_100_000:
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse({"detail": "Request too large"}, status_code=413)
            if any(Provider(role, "mock")._secret_in(raw) for role in ("target", "planner", "judge")):
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse({"detail": "Credential detected in input; refused persistence"}, status_code=422)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "no-cache"
        return response

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/api/v1/health")
    def health():
        heartbeat = store.root / "worker-heartbeat.json"
        alive = heartbeat.exists() and time.time()-heartbeat.stat().st_mtime < 10
        return {"status": "ok", "worker_alive": alive, "version": "3.0", "global_parallelism": 10}

    @app.get("/api/v1/config")
    def config():
        return {"defaults": CampaignSpec().model_dump(), "roles": [Provider(r, "live").public() for r in ("target", "planner", "judge")],
                "live_calls_automatic_on_startup": False, "wiki_url": "http://localhost:3000", "wiki_api_url": "http://localhost:8000",
                "scope": "single operator, loopback only"}

    @app.get("/api/v1/templates")
    def templates():
        return {"cards": catalog(), "prompts": ROLE_PROMPTS}

    @app.post("/api/v1/preflight")
    def check(spec: CampaignSpec):
        return preflight(spec)

    @app.get("/api/v1/campaigns")
    def campaigns():
        return {"campaigns": store.list()}

    @app.post("/api/v1/campaigns", status_code=201)
    def create(spec: CampaignSpec):
        sources = [knowledge.read(i) for i in spec.knowledge_ids]
        if any(s["freshness"] == "stale" for s in sources):
            raise ValueError("Stale sources cannot support a new research plan")
        # Full source bytes remain on disk; bounded excerpts and hashes enter Planner only.
        scoped = [{**s, "text": s["text"][:1200]} for s in sources]
        return {"id": engine.create(spec, scoped)}

    @app.get("/api/v1/campaigns/{campaign}")
    def snapshot(campaign: str, include_calls: bool = True):
        state = store.snapshot(campaign, include_calls)
        state["defense"] = store.get_artifact(campaign, "defense_report")
        return state

    @app.post("/api/v1/campaigns/{campaign}/actions/{action}")
    def action(campaign: str, action: str):
        if action == "start":
            engine.start(campaign)
        elif action in {"pause", "resume", "cancel"}:
            if action == "resume":
                from .engine import manifest
                if store.get_artifact(campaign, "manifest") != manifest():
                    raise ValueError("Runner changed; continuation requires a new campaign")
            store.control(campaign, action)
        else:
            raise HTTPException(404, "Unknown action")
        return store.snapshot(campaign, False)

    @app.post("/api/v1/campaigns/{campaign}/reviews/{candidate}")
    def record_review(campaign: str, candidate: str, body: ReviewInput):
        return review(store, campaign, candidate, body)

    @app.post("/api/v1/campaigns/{campaign}/annotations/{candidate}")
    def record_annotation(campaign: str, candidate: str, body: AnnotationInput):
        return annotate(store, campaign, candidate, body)

    @app.post("/api/v1/campaigns/{campaign}/export")
    def export(campaign: str):
        exports = store.root / "exports"
        exports.mkdir(exist_ok=True)
        archive = export_bundle(store, campaign, exports / uid("research"))
        return {"download": "/api/v1/downloads/" + archive.name}

    @app.get("/api/v1/downloads/{name}")
    def download(name: str):
        import re
        if not re.fullmatch(r"research-[a-f0-9]{32}\.zip", name):
            raise HTTPException(404)
        path = store.root / "exports" / name
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, filename=name)

    @app.get("/api/v1/events")
    async def events(request: Request, after: int = 0, campaign: str | None = None):
        try:
            cursor = max(after, int(request.headers.get("last-event-id", "0")))
        except ValueError:
            raise HTTPException(422, "Invalid event cursor")
        async def stream():
            nonlocal cursor
            started = time.monotonic()
            while time.monotonic()-started < 45 and not await request.is_disconnected():
                for event in store.events(cursor, campaign):
                    cursor = event["seq"]
                    yield f"id: {cursor}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)
        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/v1/knowledge")
    def sources(q: str = ""):
        return {"sources": knowledge.list(q), "wiki_url": "http://localhost:3000", "same_workspace": True}

    @app.post("/api/v1/knowledge")
    def import_source(body: SourceInput):
        return knowledge.ingest(body.title, body.text, body.license, body.source_url)

    @app.post("/api/v1/campaigns/{campaign}/wiki")
    def sync(campaign: str):
        state = store.snapshot(campaign)
        if state["status"] in {"draft", "running"}:
            raise ValueError("Pause or finish before snapshot sync")
        return {"page": knowledge.sync(state), "status": "candidate"}

    @app.get("/api/v1/legacy")
    def legacy():
        # Delegate to the established read-only adapter; never migrate historical evidence.
        import importlib.util
        module_path = root / "workbench/apertus-workbench/local_lab.py"
        if not module_path.is_file():
            return {"status": "not_mounted", "stores": [], "message": "Historical apps/ledgers are not bundled into the standalone runtime"}
        spec = importlib.util.spec_from_file_location("apertus_legacy_lab", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        workspace = module.Workspace(root, root / "management/lab-workspace.json")
        return workspace.snapshot()

    frontend = root / "workbench/research-ui/dist"
    if (frontend / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}")
    def index(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        if not (frontend / "index.html").is_file():
            raise HTTPException(503, "Build workbench/research-ui first, or use its Vite development server")
        return FileResponse(frontend / "index.html")

    return app
