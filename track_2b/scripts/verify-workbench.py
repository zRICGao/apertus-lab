"""Black-box local API acceptance. Always creates mock campaigns, never live calls."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8770")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/results/workbench-acceptance")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.scheme != "http":
        raise ValueError("Acceptance is limited to the local workbench")
    def api(path, data=None):
        req = Request(args.url + "/api/v1" + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    from apertus_lab.platform.contracts import CampaignSpec, Limits
    health = api("/health")
    assert health["worker_alive"], health
    assert len(api("/templates")["cards"]) == 27
    spec = CampaignSpec(title="API / Docker offline acceptance", directions=["facts"], languages=["en"], families=["false_premise"],
                        max_depth=0, defense_enabled=False, confirmation_repeats=2, min_failures=2,
                        limits=Limits(total_calls=20, planning=4, exploration=8, confirmation=8, defense=0)).model_dump()
    assert api("/preflight", spec)["network_called"] is False
    campaign = api("/campaigns", spec)["id"]
    api(f"/campaigns/{campaign}/actions/start", {})
    deadline = time.monotonic()+90
    while True:
        state = api("/campaigns/" + campaign)
        if state["status"] != "running":
            break
        if time.monotonic() > deadline:
            raise TimeoutError("Mock worker did not finish")
        time.sleep(.3)
    assert state["status"] == "completed", state["status"]
    assert state["candidates"][0]["status"] == "repeated_supported"
    assert all(c["response"]["mode"] == "mock" for c in state["calls"])
    archive_url = api(f"/campaigns/{campaign}/export", {})["download"]
    output = args.output / campaign
    output.mkdir(parents=True, exist_ok=False)
    with urlopen(args.url + archive_url, timeout=30) as response:
        (output / "research.zip").write_bytes(response.read())
    with zipfile.ZipFile(output / "research.zip") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
        assert manifest["official_findings"] == 0
        frozen = json.loads(archive.read("track_1a/data/frozen.json"))
        # Extract only safe members into an acceptance-owned directory.
        for name in archive.namelist():
            dest = (output / "package" / name).resolve()
            assert dest.is_relative_to((output / "package").resolve())
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(name))
    from apertus_lab.platform.replay import replay
    replay_result = replay(frozen, output / "standalone-replay")
    assert replay_result["calls"] == 4
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=5)
    connection.request("GET", f"/api/v1/events?campaign={campaign}&after=0")
    response = connection.getresponse()
    first = response.readline().decode().strip()
    assert first.startswith("id: "), first
    connection.close()
    result = {"campaign": campaign, "status": state["status"], "mode": "mock", "calls": len(state["calls"]),
              "usage": state["usage"], "independent_replay_calls": replay_result["calls"], "export_hashes_verified": len(manifest["files"]),
              "sse_first_event": first, "official_findings": 0, "url": args.url}
    (output / "acceptance.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
