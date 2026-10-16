"""Bounded paired dispatch; all in-flight results settle before the next batch."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import time
from typing import Callable

from .contracts import digest
from .live_contracts import request_body, schedule, validate_spec
from .live_store import LiveStore, execution_lock
from .live_transport import CSCSClient, assess
from .store import BudgetExhausted


def _batches(spec: dict, phase: str) -> list[list[dict]]:
    """Keep each matched pair together and limit concurrent pair groups."""
    groups: dict[tuple[int, str], list[dict]] = {}
    for item in schedule(spec, phase):
        key = (item["repeat"], item["case"]["pair"])
        groups.setdefault(key, []).append(item)
    if any(len(group) != 2 for group in groups.values()):
        raise ValueError("Every dispatch group must contain a control and probe")
    pair_capacity = spec["dispatch"]["max_in_flight"] // 2
    ordered = list(groups.values())
    return [[item for group in ordered[i:i + pair_capacity] for item in group]
            for i in range(0, len(ordered), pair_capacity)]


def _send(client: CSCSClient, body: dict, timeout: float, expected: str,
          case: dict, evaluator: str) -> dict:
    try:
        return assess(client.send(body, timeout), body, expected, case, evaluator)
    except Exception:
        # No exception text is stored: a transport or mock may include credentials.
        return {"mode": "live", "assessment": "error", "reason": "worker_error", "sent": True}


def execute_paired_parallel(store: LiveStore, spec: dict, client: CSCSClient,
                            replay_of: str | None = None,
                            on_start: Callable | None = None) -> str:
    spec = validate_spec(spec)
    if spec.get("dispatch", {}).get("mode") != "paired_parallel":
        raise ValueError("Expected paired parallel dispatch")
    for case in spec["cases"]:
        client.check_request(request_body(spec, case))
    with execution_lock(store.root):
        run_id = store.start(spec, replay_of)
        if on_start:
            on_start(run_id)
        run = store.read_run(run_id)
        deadline = time.monotonic() + max(0, run["deadline"] - time.time())
        status = "completed"
        try:
            with ThreadPoolExecutor(max_workers=spec["dispatch"]["max_in_flight"]) as pool:
                for batch_number, batch in enumerate(_batches(spec, run["phase"])):
                    remaining = min(deadline - time.monotonic(), run["deadline"] - time.time())
                    if remaining <= 0:
                        status = "deadline_exceeded"
                        break
                    reserved = []
                    try:
                        for item in batch:
                            body = request_body(spec, item["case"])
                            request = {"slot": item["slot"], "repeat": item["repeat"],
                                       "case": item["case"], "body": body,
                                       "endpoint": spec["target"]["endpoint"],
                                       "body_sha256": digest(body), "mode": "live",
                                       "dispatch": {"mode": "paired_parallel", "batch": batch_number,
                                                    "max_in_flight": spec["dispatch"]["max_in_flight"]},
                                       "timeout_seconds": min(spec["limits"]["request_seconds"], remaining)}
                            attempt_id = store.reserve_slot(run_id, item, request)
                            reserved.append((attempt_id, item, body, request["timeout_seconds"]))
                    except (BudgetExhausted, TimeoutError, RuntimeError):
                        # A partial batch is not sent. Its reserved slots remain spent.
                        for attempt_id, _, _, _ in reserved:
                            store.finish(attempt_id, {"mode": "live", "assessment": "error",
                                                      "reason": "batch_not_sent", "sent": False})
                        current = store.read_run(run_id)
                        status = ("cancelled" if current["cancelled"] else
                                  "deadline_exceeded" if time.time() >= run["deadline"] else
                                  "budget_exhausted")
                        break
                    if time.monotonic() >= deadline or store.read_run(run_id)["cancelled"]:
                        for attempt_id, _, _, _ in reserved:
                            store.finish(attempt_id, {"mode": "live", "assessment": "error",
                                                      "reason": "batch_not_sent", "sent": False})
                        status = "cancelled" if store.read_run(run_id)["cancelled"] else "deadline_exceeded"
                        break
                    # The request is in flight from submission onward. Cancellation cannot
                    # revoke it; every completed response is persisted before another batch.
                    futures = [(attempt_id, pool.submit(_send, client, body,
                                                        min(timeout, max(0.001, deadline - time.monotonic())),
                                                        item["case"]["expected"], item["case"],
                                                        spec["evaluator"]))
                               for attempt_id, item, body, timeout in reserved]
                    results = []
                    for attempt_id, future in futures:
                        result = future.result()
                        store.finish(attempt_id, result)
                        results.append(result)
                    first_problem = next((r["reason"] for r in results
                                          if r["assessment"] in {"error", "inconclusive"}), None)
                    if first_problem:
                        status = first_problem
                        break
                    if time.monotonic() >= deadline:
                        status = "deadline_exceeded"
                        break
                    if store.read_run(run_id)["cancelled"]:
                        status = "cancelled"
                        break
            if store.read_run(run_id)["cancelled"]:
                status = "cancelled"
        except KeyboardInterrupt:
            store.cancel(run_id)
            status = "cancelled"
        except Exception:
            store.close_run(run_id, "internal_error")
            raise RuntimeError(f"Parallel run stopped; inspect {run_id}") from None
        store.close_run(run_id, status)
        return run_id
