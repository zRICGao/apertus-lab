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
from .model_registry import ModelRegistry
from .probe_catalog import DOMAINS, SUGGESTION_SYSTEM, ANALYSIS_SYSTEM
from .providers import ConfiguredProvider
from .store import Store, uid
from .templates import catalog


class SourceInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=1_000_000)
    license: str = Field(min_length=1, max_length=200)
    source_url: str = Field(default="", max_length=2000)


class ModelInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=240)
    base_url: str = Field(min_length=10, max_length=2000)
    api_key: str = Field(min_length=1, max_length=1000)


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=240)
    base_url: str | None = Field(default=None, min_length=10, max_length=2000)
    api_key: str | None = Field(default=None, max_length=1000)


class ProbeJobInput(BaseModel):
    domain_id: str = Field(min_length=1, max_length=80)
    prompt: str = Field(min_length=1, max_length=24000)
    languages: list[str] = Field(min_length=1, max_length=12)
    target_model_id: str = Field(min_length=1, max_length=100)
    assistant_model_id: str = Field(min_length=1, max_length=100)


class ProbeSuggestionInput(BaseModel):
    domain_id: str = Field(min_length=1, max_length=80)
    context: str = Field(default="", max_length=12000)
    assistant_model_id: str = Field(min_length=1, max_length=100)
    confirmed: bool = False


class ProbeAnalysisInput(BaseModel):
    assistant_model_id: str = Field(min_length=1, max_length=100)
    confirmed: bool = False


def create_app(root: Path, store_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="Apertus Research Workbench", version="3.0.0")
    store = Store(store_root or Path(os.environ.get("WORKBENCH_DATA", root / "experiments/runs/workbench-v3")))
    engine = Engine(store)
    models = ModelRegistry(store.root)
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
                "models": models.public(), "probe_domains": DOMAINS,
                "live_calls_automatic_on_startup": False, "wiki_url": "http://localhost:3000", "wiki_api_url": "http://localhost:8000",
                "scope": "single operator, loopback only"}

    @app.get("/api/v1/models")
    def model_list():
        return models.public()

    @app.post("/api/v1/models", status_code=201)
    def model_add(body: ModelInput):
        models.add(body.model_dump())
        return models.public()

    @app.patch("/api/v1/models/{profile_id}")
    def model_update(profile_id: str, body: ModelUpdate):
        models.update(profile_id, body.model_dump(exclude_unset=True))
        return models.public()

    @app.delete("/api/v1/models/{profile_id}")
    def model_delete(profile_id: str):
        models.remove(profile_id)
        return models.public()

    @app.post("/api/v1/models/{profile_id}/select-{role}")
    def model_select(profile_id: str, role: str):
        return models.select(profile_id, role)

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

    @app.get("/api/v1/probe/domains")
    def probe_domains():
        return {"domains": DOMAINS}

    @app.post("/api/v1/probe/suggestions")
    def probe_suggestion(body: ProbeSuggestionInput):
        if not body.confirmed:
            raise ValueError("Explicit confirmation is required before suggestion calls")
        domain = next((d for d in DOMAINS if d["id"] == body.domain_id), None)
        if not domain:
            raise ValueError("Unknown Probe domain")
        profile = models.get(body.assistant_model_id)
        request = {"model": profile["model"], "messages": [{"role": "system", "content": SUGGESTION_SYSTEM},
                    {"role": "user", "content": json.dumps({"domain": domain, "context": body.context}, ensure_ascii=False)}],
                   "temperature": 0.7, "max_tokens": 1200, "stream": False}
        result = ConfiguredProvider("assistant", profile).send(request, {"kind": "suggestion"}, 120)
        if not result.get("valid"):
            return {"status": "failed", "response": result}
        try:
            suggestion = json.loads(result["text"])
        except (ValueError, TypeError):
            suggestion = {"prompt": result["text"], "rationale": "Model returned non-JSON suggestion", "variables": [], "limitations": "Needs human review"}
        return {"status": "completed", "suggestion": suggestion, "model": {"id": profile["id"], "name": profile["name"], "model": profile["model"]}}

    @app.post("/api/v1/probe/jobs", status_code=201)
    def probe_create(body: ProbeJobInput):
        if not any(d["id"] == body.domain_id for d in DOMAINS):
            raise ValueError("Unknown Probe domain")
        languages = []
        for language in body.languages:
            value = language.strip().lower()
            if not value or len(value) > 35 or value in languages:
                continue
            languages.append(value)
        if not languages or len(languages) > 12:
            raise ValueError("Choose between one and twelve languages")
        models.get(body.target_model_id); models.get(body.assistant_model_id)
        return {"id": store.probe_create(body.domain_id, body.prompt, languages, body.target_model_id, body.assistant_model_id)}

    @app.get("/api/v1/probe/jobs/{job}")
    def probe_snapshot(job: str):
        return store.probe_get(job)

    @app.post("/api/v1/probe/jobs/{job}/start-test")
    def probe_start_test(job: str, body: dict):
        store.probe_start_test(job, bool(body.get("confirmed")))
        return store.probe_get(job)

    @app.post("/api/v1/probe/jobs/{job}/save")
    def probe_save(job: str):
        state = store.probe_get(job)
        if state["status"] not in {"completed", "partial"}:
            raise ValueError("Probe job is not ready to save")
        payload = {"job": job, "domain_id": state["domain"], "prompt": state["prompt"], "languages": state["languages"],
                   "target_model_id": state["target_model_id"], "calls": state["calls"], "created": state["created"], "analysis": state.get("analysis")}
        return {"id": store.probe_save(job, payload), "path": "WORKBENCH_DATA/probe-records/" + job}

    @app.post("/api/v1/probe/jobs/{job}/discard")
    def probe_discard(job: str):
        store.probe_discard(job)
        return store.probe_get(job)

    @app.post("/api/v1/probe/jobs/{job}/analysis")
    def probe_analysis(job: str, body: ProbeAnalysisInput):
        if not body.confirmed:
            raise ValueError("Explicit confirmation is required before analysis calls")
        state = store.probe_get(job)
        if state["status"] not in {"completed", "partial"} or not state.get("saved"):
            raise ValueError("Save a completed Probe result before analysis")
        profile = models.get(body.assistant_model_id)
        evidence = {"domain": state["domain"], "prompt": state["prompt"], "languages": state["languages"], "calls": state["calls"]}
        request = {"model": profile["model"], "messages": [{"role": "system", "content": ANALYSIS_SYSTEM},
                    {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)[:24000]}], "temperature": 0, "max_tokens": 1600, "stream": False}
        result = ConfiguredProvider("assistant", profile).send(request, {"kind": "analysis"}, 120)
        if not result.get("valid"):
            raise ValueError(result.get("reason", "Analysis provider failed"))
        try:
            parsed = json.loads(result["text"])
        except (ValueError, TypeError):
            parsed = {"status": "needs_review", "observed_behavior": result["text"], "evidence": [], "alternative_explanations": [], "severity_screen": "unknown", "limitations": "Non-JSON response", "needs_human_review": True}
        return {"id": store.probe_analysis(job, {"model": profile["model"], "request": {"model": profile["model"], "message_count": len(request["messages"])}, "analysis": parsed, "raw": result["text"]})}

    @app.get("/api/v1/probe/records")
    def probe_records(domain: str = "", model: str = "", language: str = "", status: str = ""):
        return {"records": store.probe_records(domain=domain, model=model, language=language, status=status)}

    @app.get("/api/v1/probe/records/{record_id}")
    def probe_record(record_id: str):
        with store.connect() as db:
            row = db.execute("SELECT payload,job FROM probe_records WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Unknown Probe record")
        value = json.loads(row[0])
        with store.connect() as db:
            analysis = db.execute("SELECT payload FROM probe_analyses WHERE job=? ORDER BY created DESC LIMIT 1", (row[1],)).fetchone()
        value["analysis"] = json.loads(analysis[0]) if analysis else None
        return value

    @app.get("/api/v1/probe/records/{record_id}/export")
    def probe_record_export(record_id: str, format: str = "json"):
        with store.connect() as db:
            row = db.execute("SELECT payload FROM probe_records WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Unknown Probe record")
        path = store.root / "probe-records"; path.mkdir(exist_ok=True)
        payload = json.loads(row[0])
        if format.lower() not in {"json", "markdown", "md"}:
            raise HTTPException(422, "format must be json or markdown")
        if format.lower() in {"markdown", "md"}:
            output = path / (record_id + ".md")
            lines = [f"# Probe record {record_id}", "", f"- Domain: `{payload.get('domain_id', '')}`", f"- Languages: {', '.join(payload.get('languages', []))}", f"- Target model: `{payload.get('target_model_id', '')}`", "", "## Original prompt", "", "```text", str(payload.get("prompt", "")), "```", ""]
            for call in payload.get("calls", []):
                lines += [f"## {call.get('phase', 'call')} / {call.get('language', '')}", "", f"Status: `{call.get('status', 'unknown')}`", "", "### Request", "", "```json", json.dumps(call.get("request", {}), ensure_ascii=False, indent=2), "```", "", "### Response", "", "```json", json.dumps(call.get("response"), ensure_ascii=False, indent=2), "```", ""]
            output.write_text("\n".join(lines), encoding="utf-8")
            return FileResponse(output, filename=output.name, media_type="text/markdown")
        output = path / (record_id + ".json")
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return FileResponse(output, filename=output.name, media_type="application/json")

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
