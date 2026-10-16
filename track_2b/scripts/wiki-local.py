"""Start the pinned full LLM Wiki application on loopback, same research workspace."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time
import runpy
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "knowledge/llmwiki"
WORKSPACE = ROOT / "experiments/wiki-workspace"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--index-existing" in sys.argv:
        db_path = WORKSPACE / ".llmwiki/index.db"
        with sqlite3.connect(db_path) as db:
            workspace_id, user_id = db.execute("SELECT id,user_id FROM workspace LIMIT 1").fetchone()
        functions = runpy.run_path(str(APP / "llmwiki"))
        # Pinned native indexer adds missing cache rows; it does not delete any
        # source, existing document, annotation or previously indexed page.
        functions["_index_existing_files"](WORKSPACE, db_path, user_id, workspace_id)
        return
    python = APP / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    if not python.is_file():
        raise SystemExit("Install the pinned LLM Wiki dependencies in knowledge/llmwiki/.venv first; see its README.")
    node = shutil.which("node")
    next_js = APP / "web/node_modules/next/dist/bin/next"
    if not node or not next_js.is_file():
        raise SystemExit("Install Node and run npm ci in knowledge/llmwiki/web first.")
    env = {**os.environ, "MODE": "local", "WORKSPACE_PATH": str(WORKSPACE), "DATABASE_URL": "",
           "APP_URL": "http://localhost:3000", "API_URL": "http://127.0.0.1:8000", "NEXT_PUBLIC_MODE": "local",
           "NEXT_PUBLIC_API_URL": "http://127.0.0.1:8000", "NEXT_TELEMETRY_DISABLED": "1", "PYTHONIOENCODING": "utf-8", "SENTRY_DSN": "", "LOGFIRE_TOKEN": ""}
    if not (WORKSPACE / ".llmwiki/index.db").exists():
        subprocess.run([str(python), str(APP / "llmwiki"), "init", str(WORKSPACE)], check=True, env=env)
    subprocess.run([str(python), str(Path(__file__).resolve()), "--index-existing"], check=True, env=env)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    children = []
    logs = ROOT / "experiments/results/wiki-local-logs"
    logs.mkdir(parents=True, exist_ok=True)
    streams = []
    try:
        streams = [(logs / name).open("a", encoding="utf-8") for name in ("api.log", "web.log")]
        children.append(subprocess.Popen([str(python), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=APP / "api", env=env, creationflags=flags, stdout=streams[0], stderr=subprocess.STDOUT))
        children.append(subprocess.Popen([node, str(next_js), "dev", "--webpack", "--hostname", "127.0.0.1", "--port", "3000"], cwd=APP / "web", env=env, creationflags=flags, stdout=streams[1], stderr=subprocess.STDOUT))
        print("Full LLM Wiki: http://localhost:3000 (API 8000); local workspace; no model requests on startup", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            child.wait(timeout=15)
        for stream in streams:
            stream.close()


if __name__ == "__main__":
    main()
