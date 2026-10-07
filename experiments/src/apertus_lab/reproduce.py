"""Standalone judge-oriented entry point; does not import Wiki or workbench."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

from .contracts import canonical, digest, identifier
from .live import confirmation_summary, execute
from .live_contracts import validate_spec
from .live_store import LiveStore
from .live_transport import CSCSClient


def resolve_spec(template: dict, experiment_id: str | None) -> dict:
    """Give an explicitly new reproduction its own identity; preserve all other fields."""
    spec = dict(validate_spec(template))
    if experiment_id == "auto":
        suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
        spec["id"] = template["id"][:80 - len(suffix) - 1] + "-" + suffix
    elif experiment_id is not None:
        spec["id"] = identifier(experiment_id)
    return validate_spec(spec)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen exploration and independent confirmation")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--experiment-id", default=os.environ.get("EXPERIMENT_ID"),
                        help="auto creates a new experiment; an explicit ID preserves duplicate protection")
    args = parser.parse_args()
    template = validate_spec(json.loads(args.spec.read_text(encoding="utf-8-sig")))
    spec = resolve_spec(template, args.experiment_id)
    client = CSCSClient()
    store = LiveStore(args.store)
    def emit(rid: str) -> None:
        record = {"started_run_id": rid, "experiment_id": spec["id"],
                  "template_id": template["id"], "template_sha256": digest(template),
                  "spec_sha256": digest(spec), "spec": spec}
        with (args.store / f"launch-{rid}.json").open("xb") as handle:
            handle.write(canonical(record))
        print(json.dumps({"started_run_id": rid, "experiment_id": spec["id"]}), flush=True)
    first = execute(store, spec, client, on_start=emit)
    first_run = store.read_run(first)
    if first_run["status"] != "completed":
        print(json.dumps({"run_id": first, "status": first_run["status"]}))
        return 2
    second = execute(store, spec, client, replay_of=first, on_start=emit)
    second_run = store.read_run(second)
    if second_run["status"] != "completed":
        print(json.dumps({"run_id": second, "status": second_run["status"]}))
        return 2
    result = {"experiment_id": spec["id"], "template_id": template["id"],
              "exploration_id": first, "confirmation_id": second,
              "summary": confirmation_summary(first_run, second_run)}
    output = args.store / f"summary-{second}.json"
    with output.open("xb") as handle:
        handle.write(canonical(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
