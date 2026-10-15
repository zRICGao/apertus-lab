"""Independent target-only replay. No scheduler, UI, Wiki or research model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid

from apertus_lab.contracts import canonical
from .evaluation import assess
from .providers import Provider


def replay(frozen: dict, output: Path, live: bool = False) -> dict:
    if frozen["mode"] == "live" and not live:
        raise ValueError("Live frozen cases require explicit --live")
    if frozen["mode"] == "mock" and live:
        raise ValueError("Cannot relabel mock discovery as live reproduction")
    output.mkdir(parents=True, exist_ok=False)
    provider = Provider("target", frozen["mode"])
    provider.validate()
    spec = frozen["spec"]
    required = sum(c["repetitions"] * 2 * spec["max_turns"] for c in frozen["cases"])
    if required > spec["limits"]["confirmation"]:
        raise ValueError("Frozen replay exceeds declared confirmation budget; no requests sent")
    deadline = time.monotonic() + spec["limits"]["run_seconds"]
    rows = []
    (output / "frozen.json").write_bytes(canonical(frozen))
    for case_index, entry in enumerate(frozen["cases"]):
        card = entry["card"]
        for repeat in range(entry["repetitions"]):
            for part in ("control", "probe"):
                messages = [{"role": "user", "content": card[part]}]
                for turn in range(spec["max_turns"]):
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Replay deadline reached; persisted attempts remain")
                    request = {"model": provider.model, "messages": messages, "temperature": 0,
                               "max_tokens": spec["limits"]["output_tokens"], "stream": False}
                    if sum(len(m["content"]) for m in messages) > spec["limits"]["input_chars"]:
                        raise ValueError("Replay context exceeds frozen input bound")
                    slot = f"{case_index}-{repeat}-{part}-{turn}"
                    (output / (slot + "-request.json")).write_bytes(canonical(request))
                    response = provider.send(request, {"card": card, "part": part, "kind": "target"}, min(spec["limits"]["request_seconds"], deadline-time.monotonic()))
                    (output / (slot + "-response.json")).write_bytes(canonical(response))
                    rows.append({"case": card["id"], "repeat": repeat, "part": part, "turn": turn, **assess(response, card["rubric"])})
                    if not response.get("valid"):
                        break
                    messages = messages + [{"role": "assistant", "content": response["text"]}, {"role": "user", "content": card["followup"]}]
    summary = {"mode": frozen["mode"], "calls": len(rows), "rows": rows, "finding_promotion": False,
               "frozen_hash": hashlib.sha256(canonical(frozen)).hexdigest(), "observation_time": time.time()}
    (output / "summary.json").write_bytes(canonical(summary))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    destination = args.output / ("replay-" + uuid.uuid4().hex)
    result = replay(json.loads(args.frozen.read_text(encoding="utf-8")), destination, args.live)
    print(json.dumps({"output": str(destination), "mode": result["mode"], "calls": result["calls"]}))


if __name__ == "__main__":
    main()
