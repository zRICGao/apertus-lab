"""Single-host durable scheduler with atomic shared reservations and append-only evidence."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid

from apertus_lab.contracts import canonical, digest


def uid(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex


def decode(row) -> dict:
    return json.loads(row[0])


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "campaigns.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY, spec TEXT NOT NULL,
                  status TEXT NOT NULL, created REAL NOT NULL, deadline REAL NOT NULL, summary TEXT NOT NULL DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, campaign TEXT NOT NULL REFERENCES campaigns(id),
                  stage TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                  priority INTEGER NOT NULL, created REAL NOT NULL, UNIQUE(campaign,kind,payload));
                CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, task TEXT NOT NULL UNIQUE REFERENCES tasks(id),
                  campaign TEXT NOT NULL, stage TEXT NOT NULL, role TEXT NOT NULL, request TEXT NOT NULL,
                  hash TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS results(call TEXT PRIMARY KEY REFERENCES calls(id), payload TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS pairs(id TEXT PRIMARY KEY, campaign TEXT NOT NULL, card TEXT NOT NULL,
                  parent TEXT, depth INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', assessment TEXT);
                CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, campaign TEXT NOT NULL, pair_id TEXT NOT NULL UNIQUE,
                  frozen TEXT NOT NULL, hash TEXT NOT NULL, status TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, candidate TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS annotations(id TEXT PRIMARY KEY, candidate TEXT NOT NULL, repeat INTEGER NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, campaign TEXT NOT NULL, kind TEXT NOT NULL,
                  payload TEXT NOT NULL, hash TEXT NOT NULL, UNIQUE(campaign,kind));
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, campaign TEXT NOT NULL,
                  kind TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS probe_jobs(id TEXT PRIMARY KEY, domain TEXT NOT NULL, prompt TEXT NOT NULL,
                  languages TEXT NOT NULL, target_model_id TEXT NOT NULL, assistant_model_id TEXT NOT NULL,
                  status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, discarded INTEGER NOT NULL DEFAULT 0,
                  saved INTEGER NOT NULL DEFAULT 0, analysis_status TEXT NOT NULL DEFAULT 'not_requested');
                CREATE TABLE IF NOT EXISTS probe_tasks(id TEXT PRIMARY KEY, job TEXT NOT NULL REFERENCES probe_jobs(id),
                  phase TEXT NOT NULL, language TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                  priority INTEGER NOT NULL DEFAULT 10, created REAL NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS probe_calls(id TEXT PRIMARY KEY, task TEXT NOT NULL UNIQUE REFERENCES probe_tasks(id),
                  job TEXT NOT NULL, phase TEXT NOT NULL, language TEXT NOT NULL, request TEXT NOT NULL, response TEXT,
                  request_hash TEXT NOT NULL, response_hash TEXT, status TEXT NOT NULL, created REAL NOT NULL, finished REAL);
                CREATE TABLE IF NOT EXISTS probe_records(id TEXT PRIMARY KEY, job TEXT NOT NULL UNIQUE REFERENCES probe_jobs(id),
                  payload TEXT NOT NULL, hash TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS probe_analyses(id TEXT PRIMARY KEY, job TEXT NOT NULL REFERENCES probe_jobs(id),
                  payload TEXT NOT NULL, hash TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS task_queue ON tasks(status,priority,created);
                CREATE INDEX IF NOT EXISTS calls_campaign ON calls(campaign,stage);
                CREATE INDEX IF NOT EXISTS probe_task_queue ON probe_tasks(status,priority,created);
            """)
            for table in ("calls", "results", "reviews", "annotations", "artifacts", "events", "probe_records", "probe_analyses"):
                for verb in ("UPDATE", "DELETE"):
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{verb} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable evidence'); END")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def event(self, db, campaign: str, kind: str, payload: dict):
        db.execute("INSERT INTO events(campaign,kind,payload,created) VALUES(?,?,?,?)",
                   (campaign, kind, canonical(payload).decode(), time.time()))

    def create(self, spec: dict, manifest: dict) -> str:
        campaign = uid("campaign")
        with self.connect() as db:
            db.execute("INSERT INTO campaigns(id,spec,status,created,deadline) VALUES(?,?,?,?,?)",
                       (campaign, canonical(spec).decode(), "draft", time.time(), 0))
            self.event(db, campaign, "created", {"spec_hash": digest(spec), "mode": spec["mode"]})
        self.artifact(campaign, "manifest", manifest)
        return campaign

    def artifact(self, campaign: str, kind: str, value: dict) -> bool:
        with self.connect() as db:
            inserted = db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?)",
                                 (uid("artifact"), campaign, kind, canonical(value).decode(), digest(value))).rowcount
            if inserted:
                self.event(db, campaign, "artifact", {"kind": kind, "hash": digest(value)})
            return bool(inserted)

    def get_artifact(self, campaign: str, kind: str):
        with self.connect() as db:
            row = db.execute("SELECT payload,hash FROM artifacts WHERE campaign=? AND kind=?", (campaign, kind)).fetchone()
            if not row:
                return None
            value = decode(row)
            if digest(value) != row["hash"]:
                raise ValueError("Artifact integrity failure")
            return value

    def task(self, campaign: str, stage: str, kind: str, payload: dict, priority: int = 10) -> str:
        serialized = canonical(payload).decode()
        with self.connect() as db:
            row = db.execute("SELECT id FROM tasks WHERE campaign=? AND kind=? AND payload=?", (campaign, kind, serialized)).fetchone()
            if row:
                return row[0]
            task_id = uid("task")
            db.execute("INSERT INTO tasks(id,campaign,stage,kind,payload,priority,created) VALUES(?,?,?,?,?,?,?)",
                       (task_id, campaign, stage, kind, serialized, priority, time.time()))
            self.event(db, campaign, "queued", {"task_id": task_id, "kind": kind, "stage": stage})
            return task_id

    def add_pair(self, campaign: str, card: dict, parent: str | None = None, depth: int = 0) -> str | None:
        with self.connect() as db:
            existing = db.execute("SELECT card FROM pairs WHERE campaign=?", (campaign,)).fetchall()
            if any(digest([decode(r)[k] for k in ("control", "probe", "rubric")]) == digest([card[k] for k in ("control", "probe", "rubric")]) for r in existing):
                self.event(db, campaign, "branch_stopped", {"parent": parent, "reason": "duplicate"})
                return None
            pair = uid("pair")
            db.execute("INSERT INTO pairs(id,campaign,card,parent,depth) VALUES(?,?,?,?,?)",
                       (pair, campaign, canonical(card).decode(), parent, depth))
        for part in ("control", "probe"):
            self.task(campaign, "exploration", "target", {"pair": pair, "part": part, "turn": 0}, 10 if not parent else 30)
        return pair

    def control(self, campaign: str, action: str):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM campaigns WHERE id=?", (campaign,)).fetchone()
            if not row:
                raise ValueError("Unknown campaign")
            status = row["status"]
            if action == "start" and status == "draft":
                deadline = time.time() + json.loads(row["spec"])["limits"]["run_seconds"]
                db.execute("UPDATE campaigns SET status='running',deadline=? WHERE id=?", (deadline, campaign))
            elif action == "resume" and status in {"paused", "provider_paused", "interrupted"}:
                if row["deadline"] <= time.time():
                    raise ValueError("Absolute campaign deadline has elapsed")
                db.execute("UPDATE campaigns SET status='running' WHERE id=?", (campaign,))
            elif action == "pause" and status == "running":
                db.execute("UPDATE campaigns SET status='paused' WHERE id=?", (campaign,))
            elif action == "cancel" and status not in {"completed", "cancelled"}:
                db.execute("UPDATE campaigns SET status='cancelled' WHERE id=?", (campaign,))
                db.execute("UPDATE tasks SET status='skipped' WHERE campaign=? AND status='pending'", (campaign,))
            else:
                raise ValueError("Invalid state transition")
            self.event(db, campaign, action, {})

    def pending(self) -> list[dict]:
        with self.connect() as db:
            db.execute("UPDATE campaigns SET status='deadline_exceeded' WHERE status='running' AND deadline<=?", (time.time(),))
            rows = db.execute("SELECT t.*,c.spec,c.deadline FROM tasks t JOIN campaigns c ON c.id=t.campaign WHERE t.status='pending' AND c.status='running' ORDER BY t.priority,t.created").fetchall()
            return [dict(r) for r in rows]

    def reserve(self, task_id: str, request: dict, role: str, global_cap: int = 10) -> str | None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT t.*,c.status AS campaign_status,c.deadline,c.spec FROM tasks t JOIN campaigns c ON c.id=t.campaign WHERE t.id=?", (task_id,)).fetchone()
            if not row or row["status"] != "pending" or row["campaign_status"] != "running" or row["deadline"] <= time.time():
                return None
            limits = json.loads(row["spec"])["limits"]
            counts = dict(db.execute("SELECT stage,count(*) FROM calls WHERE campaign=? GROUP BY stage", (row["campaign"],)).fetchall())
            if sum(counts.values()) >= limits["total_calls"] or counts.get(row["stage"], 0) >= limits[row["stage"]]:
                db.execute("UPDATE tasks SET status='budget_skipped' WHERE id=?", (task_id,))
                self.event(db, row["campaign"], "budget_exhausted", {"stage": row["stage"], "task_id": task_id})
                return None
            total_active = db.execute("SELECT count(*) FROM tasks WHERE status='sending'").fetchone()[0]
            active = db.execute("SELECT count(*) FROM tasks WHERE campaign=? AND status='sending'", (row["campaign"],)).fetchone()[0]
            if total_active >= global_cap or active >= limits["parallelism"]:
                return None
            call = uid("call")
            db.execute("INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)", (call, task_id, row["campaign"], row["stage"], role,
                       canonical(request).decode(), digest(request), time.time()))
            db.execute("UPDATE tasks SET status='sending' WHERE id=?", (task_id,))
            self.event(db, row["campaign"], "sending", {"task_id": task_id, "call_id": call, "role": role})
            return call

    def finish(self, call: str, result: dict):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT task,campaign FROM calls WHERE id=?", (call,)).fetchone()
            if row is None:
                raise ValueError("Unknown reservation")
            db.execute("INSERT INTO results VALUES(?,?,?)", (call, canonical(result).decode(), digest(result)))
            db.execute("UPDATE tasks SET status=? WHERE id=?", ("done" if result.get("valid") else "failed", row["task"]))
            self.event(db, row["campaign"], "response_saved", {"call_id": call, "valid": result.get("valid"), "reason": result.get("reason")})

    def recover(self):
        """Called only while holding the worker's OS lock, never by API startup."""
        with self.connect() as db:
            rows = db.execute("SELECT id,campaign FROM tasks WHERE status='sending'").fetchall()
            for row in rows:
                db.execute("UPDATE tasks SET status='unknown' WHERE id=?", (row["id"],))
                db.execute("UPDATE campaigns SET status='interrupted' WHERE id=?", (row["campaign"],))
                self.event(db, row["campaign"], "unknown_after_restart", {"task_id": row["id"], "resent": False})

    def results(self, campaign: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT c.*,t.kind,t.payload,r.payload AS response,r.hash AS response_hash FROM calls c JOIN tasks t ON t.id=c.task LEFT JOIN results r ON r.call=c.id WHERE c.campaign=? ORDER BY c.created", (campaign,)).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["request"] = json.loads(item["request"])
            if digest(item["request"]) != item["hash"]:
                raise ValueError("Request hash mismatch")
            item["payload"] = json.loads(item["payload"])
            if item["response"] is not None:
                item["response"] = json.loads(item["response"])
                if digest(item["response"]) != item["response_hash"]:
                    raise ValueError("Response hash mismatch")
            output.append(item)
        return output

    def snapshot(self, campaign: str, include_calls: bool = True) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM campaigns WHERE id=?", (campaign,)).fetchone()
            if not row:
                raise ValueError("Unknown campaign")
            out = dict(row)
            out["spec"], out["summary"] = json.loads(row["spec"]), json.loads(row["summary"])
            created = db.execute("SELECT payload FROM events WHERE campaign=? AND kind='created' ORDER BY seq LIMIT 1", (campaign,)).fetchone()
            if not created or digest(out["spec"]) != json.loads(created[0])["spec_hash"]:
                raise ValueError("Campaign specification hash mismatch")
            out["usage"] = dict(db.execute("SELECT stage,count(*) FROM calls WHERE campaign=? GROUP BY stage", (campaign,)).fetchall())
            out["task_counts"] = dict(db.execute("SELECT status,count(*) FROM tasks WHERE campaign=? GROUP BY status", (campaign,)).fetchall())
            out["pairs"] = [dict(r) for r in db.execute("SELECT * FROM pairs WHERE campaign=?", (campaign,))]
            for p in out["pairs"]:
                p["card"] = json.loads(p["card"])
                p["assessment"] = json.loads(p["assessment"]) if p["assessment"] else None
            out["candidates"] = [dict(r) for r in db.execute("SELECT * FROM candidates WHERE campaign=?", (campaign,))]
            for c in out["candidates"]:
                c["frozen"], c["summary"] = json.loads(c["frozen"]), json.loads(c["summary"])
                if digest(c["frozen"]) != c["hash"]:
                    raise ValueError("Frozen candidate hash mismatch")
                c["reviews"] = []
                for r in db.execute("SELECT payload,hash FROM reviews WHERE candidate=? ORDER BY rowid", (c["id"],)):
                    value = decode(r)
                    if digest(value) != r["hash"]:
                        raise ValueError("Review hash mismatch")
                    c["reviews"].append(value)
                c["annotations"] = []
                for r in db.execute("SELECT payload,hash FROM annotations WHERE candidate=? ORDER BY rowid", (c["id"],)):
                    value = decode(r)
                    if digest(value) != r["hash"]:
                        raise ValueError("Annotation hash mismatch")
                    c["annotations"].append(value)
            out["summary"]["confirmed_findings"] = sum(bool(c["reviews"] and c["reviews"][-1]["decision"] == "confirmed") for c in out["candidates"])
        if include_calls:
            out["calls"] = self.results(campaign)
        return out

    def list(self) -> list[dict]:
        with self.connect() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM campaigns ORDER BY created DESC")]
        return [{k: v for k, v in self.snapshot(i, False).items() if k not in {"pairs", "candidates"}} for i in ids]

    def events(self, after: int = 0, campaign: str | None = None) -> list[dict]:
        with self.connect() as db:
            if campaign:
                rows = db.execute("SELECT * FROM events WHERE seq>? AND campaign=? ORDER BY seq LIMIT 200", (after, campaign)).fetchall()
            else:
                rows = db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT 200", (after,)).fetchall()
            return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def probe_event(self, job: str, kind: str, payload: dict):
        with self.connect() as db:
            self.event(db, "probe:" + job, kind, payload)

    def probe_create(self, domain: str, prompt: str, languages: list[str], target: str, assistant: str) -> str:
        job = uid("probe")
        now = time.time()
        with self.connect() as db:
            db.execute("INSERT INTO probe_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (job, domain, prompt, canonical(languages).decode(), target, assistant, "queued", now, now, 0, 0, "not_requested"))
            for language in languages:
                task = uid("probe-task")
                payload = canonical({"job": job, "language": language}).decode()
                db.execute("INSERT INTO probe_tasks VALUES(?,?,?,?,?,?,?,?,?)", (task, job, "translation", language, payload, "pending", 10, now, now))
            self.event(db, "probe:" + job, "probe_job_created", {"job": job, "languages": languages})
            self.event(db, "probe:" + job, "probe_translation_started", {"job": job, "languages": languages})
        return job

    def probe_get(self, job: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM probe_jobs WHERE id=?", (job,)).fetchone()
            if not row:
                raise ValueError("Unknown Probe job")
            out = dict(row); out["languages"] = json.loads(out["languages"])
            tasks = [dict(r) for r in db.execute("SELECT * FROM probe_tasks WHERE job=? ORDER BY created", (job,))]
            calls = [dict(r) for r in db.execute("SELECT * FROM probe_calls WHERE job=? ORDER BY created", (job,))]
            for item in calls:
                item["request"] = json.loads(item["request"])
                item["response"] = json.loads(item["response"]) if item["response"] else None
            out["tasks"], out["calls"] = tasks, calls
            record = db.execute("SELECT payload FROM probe_records WHERE job=?", (job,)).fetchone()
            analysis = db.execute("SELECT payload FROM probe_analyses WHERE job=? ORDER BY created DESC LIMIT 1", (job,)).fetchone()
            out["record"] = json.loads(record[0]) if record else None
            out["analysis"] = json.loads(analysis[0]) if analysis else None
            out["progress"] = {"total": len(tasks), "done": sum(t["status"] in {"done", "failed", "unknown"} for t in tasks), "failed": sum(t["status"] in {"failed", "unknown"} for t in tasks)}
            return out

    def probe_pending(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT t.*,j.status AS job_status,j.target_model_id,j.assistant_model_id,j.prompt,j.domain,j.languages FROM probe_tasks t JOIN probe_jobs j ON j.id=t.job WHERE t.status='pending' AND j.status IN ('queued','running') ORDER BY t.priority,t.created").fetchall()
            return [dict(r) for r in rows]

    def probe_start_test(self, job: str, confirmed: bool):
        if not confirmed:
            raise ValueError("Explicit confirmation is required before test calls")
        with self.connect() as db:
            row = db.execute("SELECT * FROM probe_jobs WHERE id=?", (job,)).fetchone()
            if not row or row["status"] in {"discarded", "unknown"}:
                raise ValueError("Probe job cannot start")
            existing = db.execute("SELECT count(*) FROM probe_tasks WHERE job=? AND phase='test'", (job,)).fetchone()[0]
            if existing:
                return
            translations = db.execute("SELECT t.language,c.response FROM probe_tasks t JOIN probe_calls c ON c.task=t.id WHERE t.job=? AND t.phase='translation' AND t.status='done'", (job,)).fetchall()
            if not translations:
                raise ValueError("No completed translations are available")
            for item in translations:
                response = json.loads(item["response"])
                task = uid("probe-task")
                payload = canonical({"job": job, "language": item["language"], "translated_prompt": response.get("text", "")}).decode()
                db.execute("INSERT INTO probe_tasks VALUES(?,?,?,?,?,?,?,?,?)", (task, job, "test", item["language"], payload, "pending", 20, time.time(), time.time()))
            db.execute("UPDATE probe_jobs SET status='running',updated=? WHERE id=?", (time.time(), job))
            self.event(db, "probe:" + job, "probe_test_started", {"job": job, "languages": [x["language"] for x in translations]})

    def probe_latest(self, job: str, phase: str, language: str = "") -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT c.response FROM probe_calls c WHERE c.job=? AND c.phase=? AND (?='' OR c.language=?) ORDER BY c.created DESC LIMIT 1", (job, phase, language, language)).fetchone()
            return json.loads(row[0]) if row and row[0] else None

    def probe_reserve(self, task_id: str, request: dict, phase: str, language: str, global_cap: int = 10) -> str | None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            active = db.execute("SELECT (SELECT count(*) FROM tasks WHERE status='sending') + (SELECT count(*) FROM probe_tasks WHERE status='sending')").fetchone()[0]
            row = db.execute("SELECT t.*,j.status AS job_status FROM probe_tasks t JOIN probe_jobs j ON j.id=t.job WHERE t.id=?", (task_id,)).fetchone()
            if not row or row["status"] != "pending" or row["job_status"] not in {"queued", "running"} or active >= global_cap:
                return None
            call = uid("probe-call"); now = time.time()
            db.execute("INSERT INTO probe_calls VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (call, task_id, row["job"], phase, language, canonical(request).decode(), None, digest(request), None, "sending", now, None))
            db.execute("UPDATE probe_tasks SET status='sending',updated=? WHERE id=?", (now, task_id))
            db.execute("UPDATE probe_jobs SET status='running',updated=? WHERE id=?", (now, row["job"]))
            self.event(db, "probe:" + row["job"], "probe_call_started", {"call_id": call, "phase": phase, "language": language})
            return call

    def probe_finish(self, call: str, result: dict):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT task,job FROM probe_calls WHERE id=?", (call,)).fetchone()
            if not row:
                raise ValueError("Unknown Probe reservation")
            now = time.time(); encoded = canonical(result).decode()
            db.execute("UPDATE probe_calls SET response=?,response_hash=?,status=?,finished=? WHERE id=?", (encoded, digest(result), "done" if result.get("valid") else "failed", now, call))
            db.execute("UPDATE probe_tasks SET status=?,updated=? WHERE id=?", ("done" if result.get("valid") else "failed", now, row["task"]))
            self.event(db, "probe:" + row["job"], "probe_call_finished", {"call_id": call, "valid": result.get("valid"), "reason": result.get("reason")})
            event_kind = "probe_translation_finished" if db.execute("SELECT phase FROM probe_calls WHERE id=?", (call,)).fetchone()[0] == "translation" else "probe_test_finished"
            self.event(db, "probe:" + row["job"], event_kind, {"call_id": call, "valid": result.get("valid"), "reason": result.get("reason")})

    def probe_recover(self):
        with self.connect() as db:
            rows = db.execute("SELECT id,job,task FROM probe_calls WHERE status='sending'").fetchall()
            for row in rows:
                db.execute("UPDATE probe_calls SET status='unknown',finished=? WHERE id=?", (time.time(), row["id"]))
                db.execute("UPDATE probe_tasks SET status='unknown',updated=? WHERE id=?", (time.time(), row["task"]))
                db.execute("UPDATE probe_jobs SET status='unknown',updated=? WHERE id=?", (time.time(), row["job"]))
                self.event(db, "probe:" + row["job"], "probe_job_failed", {"reason": "unknown_after_restart", "resent": False})

    def probe_save(self, job: str, payload: dict) -> str:
        with self.connect() as db:
            existing = db.execute("SELECT id FROM probe_records WHERE job=?", (job,)).fetchone()
            if existing:
                return existing["id"]
            record = uid("probe-record")
            db.execute("INSERT INTO probe_records VALUES(?,?,?,?,?)", (record, job, canonical(payload).decode(), digest(payload), time.time()))
            db.execute("UPDATE probe_jobs SET saved=1,updated=? WHERE id=?", (time.time(), job))
        return record

    def probe_discard(self, job: str):
        with self.connect() as db:
            row = db.execute("SELECT saved,status FROM probe_jobs WHERE id=?", (job,)).fetchone()
            if not row:
                raise ValueError("Unknown Probe job")
            if row["saved"]:
                raise ValueError("Saved Probe results cannot be discarded")
            db.execute("UPDATE probe_jobs SET discarded=1,status='discarded',updated=? WHERE id=?", (time.time(), job))
            self.event(db, "probe:" + job, "probe_job_discarded", {"job": job})

    def probe_analysis(self, job: str, payload: dict) -> str:
        analysis = uid("probe-analysis")
        with self.connect() as db:
            db.execute("INSERT INTO probe_analyses VALUES(?,?,?,?,?)", (analysis, job, canonical(payload).decode(), digest(payload), time.time()))
            db.execute("UPDATE probe_jobs SET analysis_status='completed',updated=? WHERE id=?", (time.time(), job))
            self.event(db, "probe:" + job, "probe_analysis_finished", {"analysis": analysis})
        return analysis

    def probe_records(self, domain: str = "", model: str = "", language: str = "", status: str = "") -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT id,job,payload,created FROM probe_records ORDER BY created DESC").fetchall()
            output = []
            for r in rows:
                value = {"id": r["id"], "job": r["job"], "created": r["created"], **json.loads(r["payload"])}
                if domain and value.get("domain_id") != domain:
                    continue
                if model and value.get("target_model_id") != model:
                    continue
                if language and language not in value.get("languages", []):
                    continue
                if status and not any(c.get("status") == status for c in value.get("calls", [])):
                    continue
                analysis = db.execute("SELECT payload FROM probe_analyses WHERE job=? ORDER BY created DESC LIMIT 1", (r["job"],)).fetchone()
                value["analysis"] = json.loads(analysis[0]) if analysis else None
                output.append(value)
            return output
