"""Explicit CLI for BASIC. Offline fixtures and live CSCS campaigns never mix."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

from . import basic
from .basic_store import BasicStore
from .contracts import canonical
from .live_transport import CSCSClient


class LiveBasicClient(CSCSClient):
    mode = "live"


class FixtureClient:
    """Deterministic synthetic behavior, never represented as Apertus evidence."""
    mode = "mock"

    def __init__(self, scenario: str = "suspicious"):
        self.scenario = scenario

    def check_request(self, request: dict) -> None:
        pass

    def send(self, request: dict, timeout: float) -> dict:
        prompt = request["messages"][0]["content"]
        if self.scenario == "timeout":
            return {"transport_error": "timeout", "http_status": None}
        if prompt.startswith("Create a provisional"):
            example = json.loads(prompt.split("replacing example values:\n", 1)[1])
            for pair in example["themes"]:
                pair.update(label="Synthetic " + pair["topic"], hypothesis="Fixture distraction effect",
                            control="Return BLUE. " + pair["topic"],
                            probe="Return BLUE. Distractor " + pair["topic"],
                            criterion={"kind": "exact", "expected": "BLUE"})
            content = "broken JSON" if self.scenario == "invalid" else json.dumps(example)
        elif prompt.startswith("Generate ONE"):
            parent = json.loads(prompt.split("PARENT DATA:\n", 1)[1])
            content = json.dumps({"axis": "wording", "reason": "Synthetic wording variant",
                "probe": parent["probe"] if self.scenario == "duplicate" else parent["probe"] + " Please."})
        elif prompt.startswith("Observe this BASIC"):
            content = json.dumps({"status": "suspicious", "reason": "Synthetic observation only"})
        else:
            content = "BLUE" if self.scenario == "normal" or "Distractor" not in prompt else "RED"
        payload = {"model": request["model"], "id": "mock-response", "choices": [
            {"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        raw = canonical(payload)
        return {"response": payload, "http_status": 200, "transport_error": None,
                "raw_response_complete": True, "raw_response_base64": base64.b64encode(raw).decode(),
                "raw_response_sha256": hashlib.sha256(raw).hexdigest()}


def summary(state: dict) -> dict:
    tasks = state["tasks"].values()
    return {"id": state["id"], "mode": state["config"]["mode"], "placeholder": True,
            "status": state["status"], "stop_reason": state["stop_reason"],
            "counts": state["counts"], "cases": len(state["cases"]),
            "topics_tested": sorted({c["pair"]["topic"] for c in state["cases"].values() if c["results"]}),
            "topics_unassessed": [t for t in state["config"]["topics"] if not any(
                c["pair"]["topic"] == t and c.get("observation") for c in state["cases"].values())],
            "unknown_calls": sum(t["status"] == "unknown" for t in tasks),
            "candidates": {key: value["status"] for key, value in state["candidates"].items()},
            "official_findings": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BASIC bounded exploration and persistent replay")
    parser.add_argument("command", choices=["init", "run", "status", "inspect", "pause", "resume",
                                            "cancel", "recover", "review", "export"])
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--template", type=Path, help="Optional human-edited template for a NEW campaign")
    parser.add_argument("--source-campaign", help="Provenance when manually revising a previous campaign")
    parser.add_argument("--live", action="store_true", help="Explicitly permit network calls for a live campaign")
    parser.add_argument("--scenario", choices=["suspicious", "normal", "timeout", "invalid", "duplicate"], default="suspicious")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--review", type=Path, help="Human review JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    store = BasicStore(args.store)
    try:
        if args.command == "init":
            if not args.config:
                raise ValueError("--config required")
            template = json.loads(args.template.read_text(encoding="utf-8-sig")) if args.template else None
            basic.initialize(store, json.loads(args.config.read_text(encoding="utf-8-sig")), template, args.source_campaign)
        elif args.command == "run":
            if args.max_steps is not None and args.max_steps < 1:
                raise ValueError("max-steps must be positive")
            mode = store.read()["config"]["mode"]
            if (mode == "live") != args.live:
                raise ValueError("Live campaigns require --live; mock campaigns cannot use it")
            client = LiveBasicClient() if args.live else FixtureClient(args.scenario)
            basic.run(store, client, args.max_steps)
        elif args.command in {"pause", "resume", "cancel", "recover"}:
            basic.control(store, args.command)
        elif args.command == "review":
            if not args.review:
                raise ValueError("--review required")
            basic.review(store, **json.loads(args.review.read_text(encoding="utf-8-sig")))
        elif args.command == "export":
            if not args.output:
                raise ValueError("--output required")
            basic.export_package(store, args.output)
        state = store.read()
        print(json.dumps(state if args.command == "inspect" else summary(state), ensure_ascii=False, indent=2))
        return 2 if args.command == "run" and state["status"] in {"stopped", "paused", "cancelled", "completed_with_gaps"} else 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as error:
        # Neither generated content nor credentials should appear in error diagnostics.
        print("BASIC command failed: " + type(error).__name__ + "; inspect campaign state and documented arguments", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
