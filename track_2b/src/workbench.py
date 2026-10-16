"""Local launcher: API and durable worker use separate processes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "track_2b/src"))

from apertus_lab.platform.providers import load_env
from apertus_lab.platform.store import Store
from apertus_lab.platform.engine import Engine
from apertus_lab.platform.contracts import CampaignSpec
from apertus_lab.platform.probe import ProbeRuntime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["serve", "worker", "demo", "status"])
    parser.add_argument("--store", type=Path, default=Path(os.environ.get("WORKBENCH_DATA", ROOT / "experiments/runs/workbench-v3")))
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    parser.add_argument("--external-worker", action="store_true")
    args = parser.parse_args()
    load_env(ROOT / ".env")
    store = Store(args.store)
    if args.command == "status":
        print(json.dumps(store.list(), ensure_ascii=False, indent=2))
    elif args.command == "demo":
        engine = Engine(store)
        campaign = engine.create(CampaignSpec(title="Offline architecture acceptance / 离线架构验收"))
        engine.start(campaign)
        heartbeat = store.root / "worker-heartbeat.json"
        if heartbeat.exists() and time.time()-heartbeat.stat().st_mtime < 10:
            while store.snapshot(campaign, False)["status"] == "running":
                time.sleep(.3)
        else:
            engine.run(until_idle=True)
        print(json.dumps({"id": campaign, "status": store.snapshot(campaign, False)["status"], "mode": "mock"}))
    elif args.command == "worker":
        stop = threading.Event()
        def signal_stop(*_):
            stop.set()
        signal.signal(signal.SIGTERM, signal_stop)
        signal.signal(signal.SIGINT, signal_stop)
        def heartbeat():
            while not stop.wait(2):
                (store.root / "worker-heartbeat.json").write_text(json.dumps({"pid": os.getpid(), "time": time.time()}), encoding="utf-8")
        threading.Thread(target=heartbeat, daemon=True).start()
        probe_stop = threading.Event()
        probe_thread = threading.Thread(target=ProbeRuntime(store).run, args=(probe_stop,), daemon=True)
        probe_thread.start()
        try:
            Engine(store).run(stop)
        finally:
            probe_stop.set()
            probe_thread.join(timeout=10)
    else:
        import uvicorn
        from apertus_lab.platform.api import create_app
        child = None
        if not args.external_worker:
            python = sys.executable if Path(sys.executable).is_file() else shutil.which("python")
            if not python:
                raise RuntimeError("Cannot locate a runnable Python executable for the worker")
            child = subprocess.Popen([python, str(Path(__file__).resolve()), "worker", "--store", str(args.store)],
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            uvicorn.run(create_app(ROOT, args.store), host=args.host, port=args.port, log_level="warning")
        finally:
            if child:
                # SIGTERM is graceful in Linux. Windows termination leaves in-flight
                # reservations unknown and the next worker seals them without resend.
                child.terminate()
                child.wait(timeout=130)


if __name__ == "__main__":
    main()
