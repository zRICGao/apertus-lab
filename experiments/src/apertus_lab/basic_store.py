"""Append-only campaign state history and model evidence, with atomic reservations."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
from .contracts import canonical, digest


class BasicStore:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "basic.sqlite3"

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, state: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS history (
                    seq INTEGER PRIMARY KEY, event TEXT NOT NULL, created REAL NOT NULL,
                    state TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS calls (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, role TEXT NOT NULL,
                    request TEXT NOT NULL, hash TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS results (
                    call_id TEXT PRIMARY KEY REFERENCES calls(id), payload TEXT NOT NULL,
                    hash TEXT NOT NULL, created REAL NOT NULL);
            """)
            for table in ("history", "calls", "results"):
                for action in ("UPDATE", "DELETE"):
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS no_{action}_{table} BEFORE {action} ON {table} "
                               "BEGIN SELECT RAISE(ABORT, 'append-only'); END")
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM history").fetchone():
                raise ValueError("Campaign already exists; resume it, do not reset its budget")
            self._append(db, "created", state)

    def _read(self, db) -> dict:
        row = db.execute("SELECT * FROM history ORDER BY seq DESC LIMIT 1").fetchone()
        if not row:
            raise ValueError("Campaign not initialized")
        state = json.loads(row["state"])
        if digest([row["previous"], row["event"], row["created"], state]) != row["hash"]:
            raise ValueError("State hash mismatch")
        return state

    def _append(self, db, event: str, state: dict) -> None:
        last = db.execute("SELECT hash FROM history ORDER BY seq DESC LIMIT 1").fetchone()
        previous = last[0] if last else ""
        created = time.time()
        db.execute("INSERT INTO history(event,created,state,previous,hash) VALUES (?,?,?,?,?)",
                   (event, created, canonical(state).decode(), previous,
                    digest([previous, event, created, state])))

    def mutate(self, event: str, operation):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._read(db)
            result = operation(state, db)
            self._append(db, event, state)
            return result

    def read(self) -> dict:
        if not self.path.is_file():
            raise ValueError("Campaign not initialized")
        with self.connect() as db:
            return self._read(db)

    def evidence(self) -> dict:
        self.read()
        with self.connect() as db:
            db.execute("BEGIN")
            previous = ""
            history = []
            for row in db.execute("SELECT * FROM history ORDER BY seq"):
                state = json.loads(row["state"])
                if row["previous"] != previous or digest([previous, row["event"], row["created"], state]) != row["hash"]:
                    raise ValueError("History chain mismatch")
                previous = row["hash"]
                history.append(dict(row))
            calls = []
            for row in db.execute("SELECT * FROM calls ORDER BY rowid"):
                request = json.loads(row["request"])
                if digest(request) != row["hash"]:
                    raise ValueError("Request hash mismatch")
                result = db.execute("SELECT * FROM results WHERE call_id=?", (row["id"],)).fetchone()
                payload = json.loads(result["payload"]) if result else None
                if result and digest(payload) != result["hash"]:
                    raise ValueError("Response hash mismatch")
                calls.append({**dict(row), "request": request, "result": payload})
            return {"history": history, "calls": calls, "history_head": previous}
