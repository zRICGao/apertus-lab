"""Exercise extracted Bun assets -> Python CLI -> replay -> Wiki in a temp workspace."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    import sys
    env = dict(os.environ, PYTHONPATH=str(ROOT / "track_2b/src"), PYTHONIOENCODING="utf-8")
    bun = ROOT / ".tools/node_modules/bun/bin/bun.exe"
    if not bun.exists():
        raise SystemExit(f"Project Bun executable not found: {bun}")
    with tempfile.TemporaryDirectory(prefix="apertus-e2e-") as tmp:
        root = Path(tmp)
        output = subprocess.check_output([
            str(bun), "run", str(ROOT / "workbench/apertus-workbench/src/demo.ts"),
            str(root / "state"),
        ], cwd=ROOT, env=env, text=True, encoding="utf-8")
        snapshot = root / "runtime.json"
        snapshot.write_text(output, encoding="utf-8")
        def cli(*args):
            return json.loads(subprocess.check_output([
                sys.executable, "-m", "apertus_lab.cli", *map(str, args),
                "--store", str(root / "evidence"),
            ], cwd=ROOT, env=env, text=True, encoding="utf-8"))
        responses = ROOT / "experiments/examples/mock-responses.json"
        run = cli("run-mock", "--spec", ROOT / "experiments/examples/mock-spec.json",
                  "--responses", responses, "--runtime-snapshot", snapshot)
        assert run["runtime_snapshot"]["ideas"][0]["status"] == "pending"
        assert run["reserved_calls"] == 2
        page = cli("compile", "--run-id", run["run_id"], "--workspace", root / "wiki")
        assert 'review_status: "candidate"' in Path(page["page"]).read_text(encoding="utf-8")
        replay = cli("replay-mock", "--run-id", run["run_id"], "--responses", responses)
        assert replay["run_id"] != run["run_id"]
        assert replay["spec_hash"] == run["spec_hash"]
        print("PASS: extracted runtime -> immutable evidence -> candidate Wiki -> fresh replay")
        print("All artifacts used a temporary directory. No live model calls.")


if __name__ == "__main__":
    main()
