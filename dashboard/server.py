"""Read-only local evidence dashboard server.

The server never imports the experiment runner and never writes to an evidence
database. Point it at a directory containing run folders:

    python dashboard/server.py --log-root D:\\Github-Helium-Peng
"""
from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator
from urllib.parse import parse_qs, urlsplit


SECRET_KEY = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]{12,})")
SECRET_FIELD = re.compile(r"(?:api[_-]?key|password|passwd|secret|authorization|credential)", re.I)


def scrub(value: Any, field: str = "") -> Any:
    """Remove secrets from arbitrary JSON without hiding ordinary token usage."""
    if SECRET_FIELD.search(field):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(k): scrub(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v, field) for v in value]
    if isinstance(value, str):
        return SECRET_KEY.sub("[redacted]", value)
    return value


def parse_json(value: str | bytes | None, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, UnicodeDecodeError):
        return default


@contextmanager
def readonly_db(path: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.8)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    try:
        yield db
    finally:
        db.close()


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceCatalog:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.assets = Path(__file__).resolve().parent

    def dbs(self) -> list[Path]:
        found: list[Path] = []
        if self.root.is_file() and self.root.name == "evidence.sqlite3":
            return [self.root]
        if not self.root.exists():
            return []
        for path in self.root.rglob("evidence.sqlite3"):
            if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(self.root):
                found.append(path.resolve())
        return sorted(set(found), key=lambda p: str(p).casefold())

    def relative_db(self, path: Path) -> str:
        return str(path.relative_to(self.root)).replace("\\", "/")

    def _base(self, db_path: Path, row: sqlite3.Row, spec: dict, outcome: dict | None,
              attempts: list[sqlite3.Row], max_calls: int, created_at: str) -> dict:
        counts = {key: 0 for key in ("pass", "fail", "error", "inconclusive", "pending")}
        for attempt in attempts:
            result = parse_json(attempt["payload"])
            key = result.get("assessment", "pending") if isinstance(result, dict) else "pending"
            counts[key if key in counts else "inconclusive"] += 1
        phase = row["phase"]
        expected = spec.get("limits", {}).get(f"{phase}_calls") or max_calls
        return scrub({
            "database": self.relative_db(db_path),
            "run_id": row["run_id"],
            "experiment_id": row["experiment_id"],
            "phase": phase,
            "replay_of": row["replay_of"],
            "status": (outcome or {}).get("status", "in_progress"),
            "created_at": created_at,
            "model": spec.get("target", {}).get("model", "unknown"),
            "service_version": spec.get("target", {}).get("service_version", "unknown"),
            "endpoint": spec.get("target", {}).get("endpoint", "unknown"),
            "evaluator": spec.get("evaluator", "unknown"),
            "hypothesis": spec.get("hypothesis", ""),
            "batch": spec.get("dispatch", {}).get("max_in_flight", 1),
            "dispatch_mode": spec.get("dispatch", {}).get("mode", "serial"),
            "counts": counts,
            "reserved_calls": len(attempts),
            "expected_calls": expected,
            "progress": round(min(1, len(attempts) / expected), 4) if expected else 0,
            "outcome": outcome,
        })

    def _open_run_rows(self, db_path: Path) -> list[dict]:
        with readonly_db(db_path) as db:
            tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
            required = {"runs", "attempts", "results", "live_runs", "live_outcomes"}
            if not required.issubset(tables):
                raise ValueError("missing evidence tables")
            rows = []
            for live in db.execute("select * from live_runs order by rowid"):
                run = db.execute("select * from runs where id=?", (live["run_id"],)).fetchone()
                if run is None:
                    continue
                spec = parse_json(run["spec"], {})
                attempts = db.execute("""select a.*, r.payload, r.created_at as finished_at
                    from attempts a left join results r on r.attempt_id=a.id
                    where a.run_id=? order by a.rowid""", (live["run_id"],)).fetchall()
                end = db.execute("select payload from live_outcomes where run_id=?", (live["run_id"],)).fetchone()
                outcome = parse_json(end[0]) if end else None
                rows.append(self._base(db_path, live, spec, outcome, attempts,
                                       run["max_calls"], run["created_at"]))
            return rows

    def runs(self) -> dict:
        rows: list[dict] = []
        errors: list[dict] = []
        for path in self.dbs():
            try:
                rows.extend(self._open_run_rows(path))
            except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
                errors.append({"database": self.relative_db(path), "error": str(exc)})
        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return {"schema_version": "1.0", "generated_at": iso_now(),
                "runs": scrub(rows), "errors": scrub(errors),
                "database_count": len(self.dbs())}

    def detail(self, database: str, run_id: str) -> dict:
        db_path = (self.root / database).resolve()
        if not db_path.is_relative_to(self.root) or db_path.name != "evidence.sqlite3" or not db_path.is_file():
            raise ValueError("invalid database path")
        with readonly_db(db_path) as db:
            live = db.execute("select * from live_runs where run_id=?", (run_id,)).fetchone()
            if live is None:
                raise ValueError("unknown run")
            run = db.execute("select * from runs where id=?", (run_id,)).fetchone()
            if run is None:
                raise ValueError("missing run")
            spec = parse_json(run["spec"], {})
            end = db.execute("select payload from live_outcomes where run_id=?", (run_id,)).fetchone()
            outcome = parse_json(end[0]) if end else None
            attempts = db.execute("""select a.*, r.payload, r.created_at as finished_at
                from attempts a left join results r on r.attempt_id=a.id
                where a.run_id=? order by a.rowid""", (run_id,)).fetchall()
            base = self._base(db_path, live, spec, outcome, attempts,
                              run["max_calls"], run["created_at"])
            records = []
            for attempt in attempts:
                request = parse_json(attempt["request"], {}) or {}
                result = parse_json(attempt["payload"], {}) if attempt["payload"] else None
                raw = None
                if isinstance(result, dict) and result.get("raw_response_base64"):
                    try:
                        decoded = base64.b64decode(result["raw_response_base64"], validate=True)
                        raw = parse_json(decoded, decoded.decode("utf-8", "replace"))
                    except (ValueError, binascii.Error, UnicodeDecodeError):
                        raw = "[raw response could not be decoded]"
                clean_result = dict(result) if isinstance(result, dict) else result
                if isinstance(clean_result, dict):
                    clean_result.pop("raw_response_base64", None)
                    clean_result.pop("raw_response_sha256", None)
                case = request.get("case", {}) if isinstance(request, dict) else {}
                body = request.get("body", {}) if isinstance(request, dict) else {}
                records.append(scrub({
                    "id": attempt["id"], "case_id": attempt["case_id"],
                    "pair": case.get("pair"), "role": case.get("role"),
                    "language": case.get("language"), "repeat": request.get("repeat"),
                    "slot": request.get("slot"), "batch": request.get("dispatch", {}).get("batch"),
                    "reserved_at": attempt["created_at"], "finished_at": attempt["finished_at"],
                    "prompt": case.get("prompt") or (body.get("messages") or [{}])[0].get("content", ""),
                    "request": {"model": body.get("model"), "temperature": body.get("temperature"),
                                "max_tokens": body.get("max_tokens"), "timeout_seconds": request.get("timeout_seconds")},
                    "text": (result or {}).get("text") if isinstance(result, dict) else None,
                    "parsed_response": (result or {}).get("response") if isinstance(result, dict) else None,
                    "raw_response": raw,
                    "assessment": (result or {}).get("assessment", "pending") if isinstance(result, dict) else "pending",
                    "reason": (result or {}).get("reason") if isinstance(result, dict) else None,
                    "judge": (result or {}).get("judge") if isinstance(result, dict) else None,
                    "transport_status": (result or {}).get("transport_status") if isinstance(result, dict) else None,
                    "transport_error": (result or {}).get("transport_error") if isinstance(result, dict) else None,
                    "response_model": (result or {}).get("response_model") if isinstance(result, dict) else None,
                    "finish_reason": (result or {}).get("finish_reason") if isinstance(result, dict) else None,
                    "usage": (result or {}).get("usage") if isinstance(result, dict) else None,
                    "duration_seconds": (result or {}).get("duration_seconds") if isinstance(result, dict) else None,
                }))
            base.update({"spec": scrub(spec), "attempts": records})
            return scrub(base)


def serve(catalog: EvidenceCatalog, host: str, port: int) -> ThreadingHTTPServer:
    assets = catalog.assets

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, payload: Any, status: int = 200, content_type: str = "application/json"):
            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") if content_type == "application/json" else payload
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if self.headers.get("Host") not in allowed:
                self.reply({"error": "local access only"}, 403)
                return
            url = urlsplit(self.path)
            try:
                if url.path == "/api/runs":
                    self.reply(catalog.runs())
                elif url.path == "/api/run":
                    args = parse_qs(url.query)
                    self.reply(catalog.detail(args["database"][0], args["run_id"][0]))
                elif url.path == "/api/health":
                    self.reply({"ok": True, "database_count": len(catalog.dbs())})
                elif url.path in {"/", "/index.html", "/app.js", "/styles.css"}:
                    file_name = "index.html" if url.path in {"/", "/index.html"} else url.path[1:]
                    mime = {"index.html": "text/html", "app.js": "text/javascript", "styles.css": "text/css"}[file_name]
                    self.reply((assets / file_name).read_bytes(), content_type=mime)
                else:
                    self.reply({"error": "not found"}, 404)
            except (KeyError, ValueError, OSError, sqlite3.Error, TypeError) as exc:
                self.reply({"error": "evidence unavailable", "detail": str(exc)}, 400)

    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a read-only Apertus evidence dashboard")
    parser.add_argument("--log-root", type=Path, default=Path.cwd(), help="directory to scan for evidence.sqlite3")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    catalog = EvidenceCatalog(args.log_root)
    with serve(catalog, args.host, args.port) as http:
        print(f"Apertus dashboard: http://{args.host}:{http.server_port}", flush=True)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
