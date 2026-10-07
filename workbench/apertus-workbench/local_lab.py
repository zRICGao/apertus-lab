"""Local integration layer. No model dispatch, no ledger writes, no finding promotion."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

from apertus_lab.contracts import canonical, digest
from apertus_lab.knowledge import check_sources, compile_candidate
from apertus_lab.live import confirmation_summary
from apertus_lab.live_store import LiveStore, execution_lock


class ReadOnlyStore(LiveStore):
    """Reuse ledger validation, with SQLite enforcing read-only access."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / "evidence.sqlite3"
        if not self.path.is_file():
            raise FileNotFoundError("Evidence store has not been created")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        try:
            yield db
        finally:
            db.close()


class Workspace:
    def __init__(self, root: Path, config: Path):
        self.root = root.resolve()
        value = json.loads(config.read_text(encoding="utf-8-sig"))
        if value.get("schema_version") != "1.0" or not isinstance(value.get("stores"), dict):
            raise ValueError("Unsupported workspace configuration")
        self.stores = {name: self.path(path) for name, path in value["stores"].items()}
        self.wiki = self.path(value["wiki_workspace"])
        self.runtime = self.path(value["runtime_state"])
        self.wiki_app = self.path(value["wiki_application"])

    def path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(self.root):
            raise ValueError("Workspace paths must remain inside the repository")
        return path

    def store(self, name: str) -> ReadOnlyStore:
        if name not in self.stores:
            raise ValueError("Unknown store")
        return ReadOnlyStore(self.stores[name])

    def runs(self, name: str) -> list[dict]:
        store = self.store(name)
        with store.connect() as db:
            ids = [row[0] for row in db.execute("SELECT run_id FROM live_runs ORDER BY rowid")]
        return [store.read_run(run_id) for run_id in ids]

    def conclusion(self, run: dict, runs: list[dict]) -> dict:
        parent = run if run["phase"] == "exploration" else next(
            (r for r in runs if r["run_id"] == run["replay_of"]), None)
        replay = next((r for r in runs if parent and r["replay_of"] == parent["run_id"]), None)
        if not parent or not replay:
            return {"status": "awaiting_confirmation"}
        try:
            return confirmation_summary(parent, replay)
        except ValueError:
            return {"status": "incomplete_or_incompatible"}

    def projection(self, name: str, run: dict, runs: list[dict]) -> dict:
        counts = {key: 0 for key in ("pass", "fail", "error", "inconclusive", "pending")}
        for attempt in run["attempts"]:
            counts[attempt["result"]["assessment"] if attempt["result"] else "pending"] += 1
        return {
            "store": name, "run_id": run["run_id"], "experiment_id": run["spec"]["id"],
            "phase": run["phase"], "status": run["status"], "created_at": run["created_at"],
            "model": run["spec"]["target"]["model"], "counts": counts,
            "reserved_calls": run["reserved_calls"], "unexecuted": len(run["unexecuted_slots"]),
            "unknown_attempts": len(run["unknown_attempts"]), "evidence_hash": digest(run),
            "conclusion": self.conclusion(run, runs)["status"], "replay_of": run["replay_of"],
        }

    def snapshot(self) -> dict:
        stores, rows = [], []
        for name, path in self.stores.items():
            if not (path / "evidence.sqlite3").is_file():
                stores.append({"name": name, "status": "not_created"})
                continue
            try:
                runs = self.runs(name)
                rows.extend(self.projection(name, run, runs) for run in runs)
                stores.append({"name": name, "status": "verified", "runs": len(runs)})
            except (ValueError, OSError, sqlite3.Error, KeyError, TypeError):
                stores.append({"name": name, "status": "unreadable_or_corrupt"})
        return {"schema_version": "1.0", "stores": stores, "runs": rows,
                "wiki": check_sources(self.wiki),
                "capabilities": {"evidence_view": True, "model_dispatch": False,
                                 "research_agent": "unconfigured", "finding_promotion": "human_review_only"}}

    def detail(self, name: str, run_id: str) -> dict:
        runs = self.runs(name)
        run = next((r for r in runs if r["run_id"] == run_id), None)
        if run is None:
            raise ValueError("Unknown run")
        result = self.projection(name, run, runs)
        result.update(hypothesis=run["spec"]["hypothesis"], summary=self.conclusion(run, runs),
                      attempts=[{"id": a["id"], "case_id": a["case_id"],
                                 "prompt": a["request"]["case"]["prompt"],
                                 "expected": a["request"]["case"]["expected"],
                                 "text": (a["result"] or {}).get("text"),
                                 "assessment": (a["result"] or {}).get("assessment", "pending"),
                                 "reason": (a["result"] or {}).get("reason"),
                                 "result_hash": a["result_hash"]} for a in run["attempts"]])
        return result

    def sync(self) -> list[dict]:
        """Rebuild derived knowledge and Memory notes without touching the ledger."""
        bun = self.root / ".tools/node_modules/bun/bin/bun.exe"
        if not bun.is_file():
            import shutil
            located = shutil.which("bun")
            if not located:
                raise ValueError("Project Bun runtime is unavailable")
            bun = Path(located)
        records = []
        with execution_lock(self.runtime):
            for name, path in self.stores.items():
                if not (path / "evidence.sqlite3").is_file():
                    continue
                runs = self.runs(name)
                for run in runs:
                    if not run["outcome"]:
                        records.append({"run_id": run["run_id"], "status": "skipped_open_run"})
                        continue
                    if not any(a["result"] for a in run["attempts"]):
                        records.append({"run_id": run["run_id"], "status": "skipped_no_results"})
                        continue
                    page = compile_candidate(self.store(name), run["run_id"], self.wiki)
                    projection = self.projection(name, run, runs)
                    directory = self.runtime / "imports"
                    directory.mkdir(parents=True, exist_ok=True)
                    target = directory / f"{run['run_id']}-{digest(projection)[:12]}.json"
                    data = canonical(projection)
                    if target.is_symlink():
                        raise ValueError("Refusing symlink projection")
                    if target.exists():
                        if target.read_bytes() != data:
                            raise ValueError("Edited projection must not be overwritten")
                    else:
                        with target.open("xb") as handle:
                            handle.write(data)
                    env = os.environ.copy()
                    env.pop("LLM_API_KEY", None)
                    completed = subprocess.run([str(bun), "run", str(Path(__file__).parent / "src/sync-run.ts"),
                                                str(self.runtime), str(target)],
                                               capture_output=True, env=env, timeout=30)
                    if completed.returncode:
                        raise RuntimeError("Memory import failed; evidence and Wiki snapshot preserved")
                    records.append({"run_id": run["run_id"], "page": str(page.relative_to(self.root)),
                                    "conclusion": projection["conclusion"], "memory": "synced"})
                for run in runs:
                    if run["phase"] == "confirmation" and run["outcome"]:
                        self.compile_pair(run, runs)
        return records

    def compile_pair(self, replay: dict, runs: list[dict]) -> None:
        parent = next((r for r in runs if r["run_id"] == replay["replay_of"]), None)
        if not parent or not any(a["result"] for a in replay["attempts"]):
            return
        summary = self.conclusion(replay, runs)
        refs = [{"path": f"sources/{r['run_id']}-{digest(r)[:12]}.json", "sha256": digest(r)}
                for r in (parent, replay)]
        name = f"run-pair-{digest({'refs': refs, 'summary': summary})[:16]}"
        metadata = {"id": name, "title": f"运行结论：{parent['spec']['id']}",
                    "description": "探索与独立重跑的自动汇总，待人工审核", "date": parent["created_at"][:10],
                    "tags": ["apertus-lab", "run-summary"], "review_status": "candidate",
                    "freshness": "current", "conclusion": summary["status"],
                    "scope": {"model": parent["spec"]["target"]["model"],
                              "languages": sorted({c["language"] for c in parent["spec"]["cases"]})},
                    "evidence_refs": refs}
        header = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in metadata.items())
        content = f"---\n{header}\n---\n\n## 运行结论\n\n`{summary['status']}`。\n\n"
        content += ("not_supported 表示本次用例没有支持预设假设；candidate 表示本文是待审核草稿。\n"
                    "候选状态不授予 finding，也不证明其他场景没有问题。\n\n## 汇总\n\n```json\n")
        content += json.dumps(summary, ensure_ascii=False, indent=2) + "\n```\n\n## 原始依据\n\n"
        content += "\n".join(f"- [运行证据 {i}](../{ref['path']})" for i, ref in enumerate(refs, 1)) + "\n"
        path = self.wiki / "wiki" / f"{name}.md"
        data = content.encode("utf-8")
        if path.is_symlink() or (path.exists() and path.read_bytes() != data):
            raise ValueError("Refusing to overwrite edited knowledge summary")
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(data)


def server(workspace: Workspace, port: int = 8765) -> ThreadingHTTPServer:
    assets = Path(__file__).parent / "web"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if self.headers.get("Host") not in allowed or (
                self.headers.get("Origin") and self.headers["Origin"] not in {"http://" + h for h in allowed}
            ):
                self.send_error(403)
                return
            url = urlsplit(self.path)
            try:
                if url.path == "/api/snapshot":
                    content, mime = canonical(workspace.snapshot()), "application/json"
                elif url.path == "/api/run":
                    args = parse_qs(url.query)
                    content = canonical(workspace.detail(args["store"][0], args["id"][0]))
                    mime = "application/json"
                elif url.path in {"/", "/app.js", "/style.css"}:
                    name = "index.html" if url.path == "/" else url.path[1:]
                    content = (assets / name).read_bytes()
                    mime = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[name]
                else:
                    self.send_error(404)
                    return
            except (ValueError, OSError, KeyError, sqlite3.Error, TypeError):
                self.send_error(400, "Unavailable or invalid evidence request")
                return
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; object-src 'none'")
            self.end_headers()
            self.wfile.write(content)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(root: Path) -> int:
    parser = argparse.ArgumentParser(description="Local Apertus workspace; no model calls")
    parser.add_argument("command", choices=["status", "sync", "serve", "wiki"])
    parser.add_argument("--config", type=Path, default=root / "management/lab-workspace.json")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        workspace = Workspace(root, args.config)
        if args.command == "serve":
            with server(workspace, args.port) as http:
                print(f"Apertus workspace: http://127.0.0.1:{http.server_port}", flush=True)
                http.serve_forever()
        elif args.command == "wiki":
            python = workspace.wiki_app / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            env = os.environ.copy()
            env.pop("LLM_API_KEY", None)
            return subprocess.call([str(python), str(workspace.wiki_app / "llmwiki"), "serve", str(workspace.wiki)], env=env)
        else:
            result = workspace.sync() if args.command == "sync" else workspace.snapshot()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if args.command == "status" and any(s["status"] == "unreadable_or_corrupt" for s in result["stores"]):
                return 2
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError) as error:
        print(f"Workspace operation failed: {type(error).__name__}", file=sys.stderr)
        return 1
