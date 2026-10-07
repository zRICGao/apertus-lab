"""Offline clean-package smoke, real CLI entry with an explicitly substituted HTTP fixture."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    module_spec = importlib.util.spec_from_file_location("release_builder", ROOT / "scripts/build-mvp-release.py")
    builder = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(builder)
    with tempfile.TemporaryDirectory(prefix="apertus-mvp-package-") as tmp:
        root = Path(tmp)
        release = builder.build(root / "release", ROOT / "experiments/examples/live-spec.json")
        track = release / "track_1a"
        env = dict(os.environ, PYTHONPATH=str(track / "src"), PYTHONIOENCODING="utf-8")
        env.pop("LLM_API_KEY", None)
        subprocess.run([sys.executable, "-m", "apertus_lab.cli", "validate-live", "--spec", "data/spec.json"],
                       cwd=track, env=env, check=True, capture_output=True)
        # This subprocess imports only the packaged source, with no Wiki/workbench imports.
        code = '''
import base64, hashlib, json, sys
import apertus_lab.reproduce as entry
class OfflineHTTPFixture:
    def check_request(self, body): pass
    def send(self, body, timeout):
        payload={"model":body["model"],"id":"offline-fixture","choices":[{"message":{"content":"BLUE"},"finish_reason":"stop"}]}
        raw=json.dumps(payload).encode()
        return {"http_status":200,"transport_error":None,"response":payload,"raw_response_base64":base64.b64encode(raw).decode(),"raw_response_sha256":hashlib.sha256(raw).hexdigest(),"raw_response_complete":True}
entry.CSCSClient=OfflineHTTPFixture
sys.argv=["reproduce","--spec","data/spec.json","--store","output"]
raise SystemExit(entry.main())
'''
        completed = subprocess.run([sys.executable, "-c", code], cwd=track, env=env,
                                   check=True, capture_output=True, text=True, encoding="utf-8")
        summaries = list((track / "output").glob("summary-*.json"))
        assert len(summaries) == 1
        summary = json.loads(summaries[0].read_text())
        assert summary["summary"]["status"] == "not_supported"
        second = summary["confirmation_id"]
        inspection = subprocess.check_output([sys.executable, "-m", "apertus_lab.cli", "inspect-live",
                                             "--store", "output", "--run-id", second], cwd=track, env=env)
        snapshot = root / "run.json"
        snapshot.write_bytes(inspection)
        run = json.loads(inspection)
        assert run["reserved_calls"] == 12 and run["status"] == "completed"
        duplicate = subprocess.run([sys.executable, "-c", code], cwd=track, env=env, capture_output=True)
        assert duplicate.returncode != 0
        bun = ROOT / ".tools/node_modules/bun/bin/bun.exe"
        board = subprocess.check_output([str(bun), "run", str(ROOT / "workbench/apertus-workbench/src/import-run.ts"),
                                         str(root / "state"), str(snapshot)], cwd=ROOT)
        assert b"completed" in board
        subprocess.run([sys.executable, "-m", "apertus_lab.cli", "compile-live", "--store", "output",
                        "--run-id", second, "--workspace", str(root / "wiki")], cwd=track, env=env,
                       check=True, capture_output=True)
        print("PASS: isolated release -> fixture exploration/replay -> no finding -> duplicate refusal -> BreachWeave summary -> candidate Wiki")
        print("18 offline fixture responses; no real model calls; temporary artifacts only. Docker not exercised.")


if __name__ == "__main__":
    main()
