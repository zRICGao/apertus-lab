"""Serial, non-resumable live execution. Crashed reservations are never replayed implicitly."""
from __future__ import annotations

import time
from typing import Callable

from .contracts import digest
from .evaluators import FAIRNESS_EVALUATOR
from .live_contracts import request_body, schedule, validate_spec
from .live_store import LiveStore, execution_lock
from .live_transport import CSCSClient, assess
from .store import BudgetExhausted


def execute(store: LiveStore, spec: dict, client: CSCSClient,
            replay_of: str | None = None, on_start: Callable | None = None) -> str:
    spec = validate_spec(spec)
    if spec.get("dispatch", {}).get("mode") == "paired_parallel":
        from .parallel_live import execute_paired_parallel
        return execute_paired_parallel(store, spec, client, replay_of, on_start)
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
            for item in schedule(spec, run["phase"]):
                remaining = min(deadline - time.monotonic(), run["deadline"] - time.time())
                if remaining <= 0:
                    status = "deadline_exceeded"
                    break
                body = request_body(spec, item["case"])
                request = {"slot": item["slot"], "repeat": item["repeat"], "case": item["case"],
                           "body": body, "endpoint": spec["target"]["endpoint"],
                           "body_sha256": digest(body), "mode": "live",
                           "timeout_seconds": min(spec["limits"]["request_seconds"], remaining)}
                try:
                    attempt_id = store.reserve_slot(run_id, item, request)
                except BudgetExhausted:
                    status = "budget_exhausted"
                    break
                except TimeoutError:
                    status = "deadline_exceeded"
                    break
                except RuntimeError as error:
                    if str(error) == "cancelled":
                        status = "cancelled"
                        break
                    raise
                # Cancellation linearizes against reservation. A reserved request is
                # in flight; cancellation never promises to revoke server work.
                remaining = min(deadline - time.monotonic(), run["deadline"] - time.time())
                if remaining <= 0:
                    store.finish(attempt_id, {"mode": "live", "assessment": "error",
                                             "reason": "deadline_before_send", "sent": False})
                    status = "deadline_exceeded"
                    break
                response = client.send(body, min(request["timeout_seconds"], remaining))
                result = assess(response, body, item["case"]["expected"], item["case"],
                                spec["evaluator"])
                store.finish(attempt_id, result)
                if result["assessment"] in {"error", "inconclusive"}:
                    status = result["reason"]
                    break
                if time.monotonic() >= deadline:
                    status = "deadline_exceeded"
                    break
            if store.read_run(run_id)["cancelled"]:
                status = "cancelled"
        except KeyboardInterrupt:
            store.cancel(run_id)
            status = "cancelled"
        except Exception:
            # Never log arbitrary exception messages: they could contain credentials.
            store.close_run(run_id, "internal_error")
            raise RuntimeError(f"Live run stopped; inspect {run_id}") from None
        store.close_run(run_id, status)
        return run_id


def confirmation_summary(exploration: dict, confirmation: dict) -> dict:
    if exploration["spec"]["evaluator"] == FAIRNESS_EVALUATOR:
        return _fairness_confirmation_summary(exploration, confirmation)
    spec = exploration["spec"]
    if (exploration["status"] != "completed" or confirmation["status"] != "completed"
            or exploration["cancelled"] or confirmation["cancelled"]
            or exploration["phase"] != "exploration" or confirmation["phase"] != "confirmation"
            or confirmation["replay_of"] != exploration["run_id"]
            or exploration["spec_hash"] != confirmation["spec_hash"]
            or exploration["manifest"]["runner_sha256"] != confirmation["manifest"]["runner_sha256"]):
        raise ValueError("Complete frozen exploration and linked replay are required")
    summaries = []
    for run in (exploration, confirmation):
        if run["unexecuted_slots"] or run["unknown_attempts"]:
            raise ValueError("Incomplete run")
        counts = {}
        for case in spec["cases"]:
            results = [a["result"]["assessment"] for a in run["attempts"] if a["case_id"] == case["id"]]
            counts[case["id"]] = {"n": len(results), **{k: results.count(k) for k in ("pass", "fail", "inconclusive", "error")}}
        summaries.append(counts)
    supported = []
    for case in spec["cases"]:
        if case["role"] != "probe":
            continue
        control = next(c for c in spec["cases"] if c["pair"] == case["pair"] and c["role"] == "control")
        controls_pass = all(s[control["id"]]["n"] == s[control["id"]]["pass"] for s in summaries)
        if (controls_pass and summaries[0][case["id"]]["fail"] >= 1
                and summaries[1][case["id"]]["fail"] >= spec["confirmation"]["min_probe_failures"]):
            supported.append(case["id"])
    return {"exploration": summaries[0], "confirmation": summaries[1],
            "supported_probe_ids": supported,
            "status": "candidate" if supported else "not_supported",
            "requires_independent_review": True}


def _fairness_confirmation_summary(exploration: dict, confirmation: dict) -> dict:
    """Compare each probe with its neutral control in both frozen runs."""
    spec = exploration["spec"]
    if (exploration["status"] != "completed" or confirmation["status"] != "completed"
            or exploration["cancelled"] or confirmation["cancelled"]
            or exploration["phase"] != "exploration" or confirmation["phase"] != "confirmation"
            or confirmation["replay_of"] != exploration["run_id"]
            or exploration["spec_hash"] != confirmation["spec_hash"]
            or exploration["manifest"]["runner_sha256"] != confirmation["manifest"]["runner_sha256"]):
        raise ValueError("Complete frozen exploration and linked replay are required")
    if exploration["unexecuted_slots"] or exploration["unknown_attempts"]:
        raise ValueError("Incomplete exploration run")
    if confirmation["unexecuted_slots"] or confirmation["unknown_attempts"]:
        raise ValueError("Incomplete confirmation run")

    def counts(run: dict) -> dict:
        result = {}
        for case in spec["cases"]:
            assessments = [a["result"]["assessment"] for a in run["attempts"]
                           if a["case_id"] == case["id"]]
            result[case["id"]] = {"n": len(assessments),
                                  **{k: assessments.count(k)
                                     for k in ("pass", "fail", "inconclusive", "error")}}
        return result

    def violations(run: dict, control: dict, probe: dict) -> list[dict]:
        by_slot = {(a["case_id"], a["request"].get("repeat", 0)): a
                   for a in run["attempts"]}
        found = []
        for repeat in range(1 if run["phase"] == "exploration" else spec["confirmation"]["repetitions"]):
            control_attempt = by_slot.get((control["id"], repeat))
            probe_attempt = by_slot.get((probe["id"], repeat))
            if not control_attempt or not probe_attempt:
                continue
            control_result, probe_result = control_attempt["result"], probe_attempt["result"]
            if control_result["assessment"] != "pass":
                continue
            if probe_result["assessment"] == "fail":
                found.append({"repeat": repeat, "type": probe_result.get("reason", "probe_fail")})
                continue
            control_judge, probe_judge = control_result.get("judge"), probe_result.get("judge")
            if (control_judge and probe_judge and control_judge.get("valid")
                    and probe_judge.get("valid")
                    and control_judge.get("decision") != probe_judge.get("decision")):
                found.append({"repeat": repeat, "type": "decision_changed_after_attribute_injection",
                              "control_decision": control_judge["decision"],
                              "probe_decision": probe_judge["decision"]})
        return found

    summaries = [counts(exploration), counts(confirmation)]
    reports, supported = [], []
    for probe in (c for c in spec["cases"] if c["role"] == "probe"):
        control = next(c for c in spec["cases"]
                       if c["pair"] == probe["pair"] and c["role"] == "control")
        control_pass = all(summary[control["id"]]["n"] == summary[control["id"]]["pass"]
                           for summary in summaries)
        exploration_violations = violations(exploration, control, probe)
        confirmation_violations = violations(confirmation, control, probe)
        if (control_pass and exploration_violations
                and len(confirmation_violations) >= spec["confirmation"]["min_probe_failures"]):
            supported.append(probe["id"])
        reports.append({"pair": probe["pair"], "control_id": control["id"],
                        "probe_id": probe["id"], "control_pass": control_pass,
                        "exploration_violations": exploration_violations,
                        "confirmation_violations": confirmation_violations})
    return {"exploration": summaries[0], "confirmation": summaries[1],
            "pair_reports": reports, "supported_probe_ids": supported,
            "status": "candidate" if supported else "not_supported",
            "requires_independent_review": True}
