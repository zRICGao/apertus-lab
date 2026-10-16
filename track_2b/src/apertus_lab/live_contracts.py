"""Strict MVP contract. Resource bounds only; no monetary configuration."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .contracts import canonical, fields, identifier, text
from .evaluators import FAIRNESS_EVALUATOR, SAFETY_EVALUATOR

MODEL = "swiss-ai/Apertus-v1.5-70B"
ENDPOINT = "https://api.inference.cscs.ch/v1"


def integer(value: Any, name: str, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")


def validate_spec(data: dict) -> dict:
    required = {"schema_version", "id", "hypothesis", "target", "cases", "limits",
                "generation", "confirmation", "evaluator"}
    allowed = required | {"dispatch", "paired_identity_controls"}
    if not required <= set(data) or set(data) - allowed:
        raise ValueError("Invalid live spec fields")
    if data["schema_version"] != "2.0":
        raise ValueError("Live requires schema_version 2.0")
    identifier(data["id"])
    text(data["hypothesis"], "hypothesis")
    target = data["target"]
    fields(target, {"model", "endpoint", "revision", "service_version"})
    if target["model"] != MODEL or target["endpoint"] != ENDPOINT:
        raise ValueError("MVP only supports the configured CSCS Apertus v1.5 70B endpoint")
    for key in ("revision", "service_version"):
        text(target[key], key)
    if data["evaluator"] not in {"exact-stripped-text-v1", FAIRNESS_EVALUATOR, SAFETY_EVALUATOR}:
        raise ValueError("Unsupported evaluator")
    paired_identity_controls = data.get("paired_identity_controls", False)
    if type(paired_identity_controls) is not bool:
        raise ValueError("paired_identity_controls must be a boolean")
    if paired_identity_controls and data["evaluator"] != FAIRNESS_EVALUATOR:
        raise ValueError("paired_identity_controls requires the fairness evaluator")
    if "dispatch" in data:
        fields(data["dispatch"], {"mode", "max_in_flight"})
        if data["dispatch"]["mode"] != "paired_parallel":
            raise ValueError("Unsupported dispatch mode")
        integer(data["dispatch"]["max_in_flight"], "max_in_flight", 2, 10)
        if data["dispatch"]["max_in_flight"] % 2:
            raise ValueError("Paired parallel dispatch requires an even in-flight cap")
    limits = data["limits"]
    fields(limits, {"exploration_calls", "confirmation_calls", "max_input_chars",
                    "run_seconds", "request_seconds"})
    for key in ("exploration_calls", "confirmation_calls"):
        integer(limits[key], key, 1, 10000)
    integer(limits["max_input_chars"], "max_input_chars", 1, 100000)
    integer(limits["run_seconds"], "run_seconds", 1, 86400)
    integer(limits["request_seconds"], "request_seconds", 1, 120)
    fields(data["generation"], {"temperature", "max_output_tokens"})
    if type(data["generation"]["temperature"]) not in (int, float) or data["generation"]["temperature"] != 0:
        raise ValueError("MVP temperature must be zero")
    integer(data["generation"]["max_output_tokens"], "max_output_tokens", 1, 1024)
    confirmation = data["confirmation"]
    fields(confirmation, {"repetitions", "min_probe_failures"})
    integer(confirmation["repetitions"], "repetitions", 2, 100)
    integer(confirmation["min_probe_failures"], "min_probe_failures", 1,
            confirmation["repetitions"])
    cases = data["cases"]
    if not isinstance(cases, list) or not cases or len(cases) > 100:
        raise ValueError("Expected 1–100 cases")
    ids, pairs = set(), {}
    case_fields = {"id", "pair", "role", "language", "prompt", "expected"}
    if data["evaluator"] == FAIRNESS_EVALUATOR:
        case_fields.add("judge")
    if data["evaluator"] == SAFETY_EVALUATOR:
        case_fields.add("judge")
    for case in cases:
        fields(case, case_fields)
        identifier(case["id"])
        identifier(case["pair"])
        if case["id"] in ids:
            raise ValueError("Duplicate case id")
        ids.add(case["id"])
        if case["role"] not in {"probe", "control"}:
            raise ValueError("Invalid case role")
        for key in ("language", "prompt", "expected"):
            text(case[key], key)
        if len(case["prompt"]) > limits["max_input_chars"]:
            raise ValueError("Case exceeds input character bound")
        if data["evaluator"] == FAIRNESS_EVALUATOR:
            judge = case["judge"]
            judge_fields = {"protected_terms", "stereotype_terms", "unsupported_markers"}
            fields(judge, judge_fields | ({"expected_decision"} if "expected_decision" in judge else set()))
            if "expected_decision" in judge and judge["expected_decision"] not in {"A", "B", "tie"}:
                raise ValueError("judge.expected_decision must be A, B, or tie")
            for key in ("protected_terms", "stereotype_terms", "unsupported_markers"):
                values = judge[key]
                if (not isinstance(values, list) or not values or len(values) > 32
                        or any(not isinstance(value, str) or not value.strip() for value in values)):
                    raise ValueError(f"judge.{key} must be a nonempty list of text")
        if data["evaluator"] == SAFETY_EVALUATOR:
            judge = case["judge"]
            fields(judge, {"refusal_terms", "tool_claim_terms", "operational_markers"})
            for key in judge:
                values = judge[key]
                if (not isinstance(values, list) or not values or len(values) > 64
                        or any(not isinstance(value, str) or not value.strip() for value in values)):
                    raise ValueError(f"judge.{key} must be a nonempty list of text")
        pairs.setdefault(case["pair"], []).append(case)
    for pair in pairs.values():
        if len(pair) != 2 or {c["role"] for c in pair} != {"probe", "control"}:
            raise ValueError("Each pair needs exactly one probe and one control")
        if len({c["language"] for c in pair}) != 1:
            raise ValueError("Matched pairs must use the same language")
        if data["evaluator"] == FAIRNESS_EVALUATOR:
            control = next(c for c in pair if c["role"] == "control")
            probe = next(c for c in pair if c["role"] == "probe")
            if control["judge"] != probe["judge"]:
                raise ValueError("Fairness pairs must share judge metadata")
            terms = [term.casefold() for term in control["judge"]["protected_terms"]]
            control_has_terms = any(term in control["prompt"].casefold() for term in terms)
            probe_has_terms = any(term in probe["prompt"].casefold() for term in terms)
            if paired_identity_controls:
                control_terms = {term for term in terms if term in control["prompt"].casefold()}
                probe_terms = {term for term in terms if term in probe["prompt"].casefold()}
                if not control_has_terms or not probe_has_terms or control_terms != probe_terms:
                    raise ValueError("Matched identity controls and probes must contain the same protected terms")
            else:
                if control_has_terms:
                    raise ValueError("Fairness control must omit protected attribute terms")
                if not probe_has_terms:
                    raise ValueError("Fairness probe must include a protected attribute term")
    if limits["exploration_calls"] < len(cases) or limits["confirmation_calls"] < len(cases) * confirmation["repetitions"]:
        raise ValueError("Call limits cannot cover the declared complete experiment")
    # Defensive copy and finite JSON validation.
    import json
    return json.loads(canonical(data))


def runner_manifest() -> dict:
    import platform
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(Path(__file__).parent.glob("*.py"))}
    return {"python": platform.python_version(), "source_hashes": files,
            "runner_sha256": hashlib.sha256(canonical(files)).hexdigest()}


def request_body(spec: dict, case: dict) -> dict:
    return {"model": spec["target"]["model"],
            "messages": [{"role": "user", "content": case["prompt"]}],
            "temperature": 0, "max_tokens": spec["generation"]["max_output_tokens"],
            "stream": False}


def schedule(spec: dict, phase: str) -> list[dict]:
    repetitions = 1 if phase == "exploration" else spec["confirmation"]["repetitions"]
    return [{"slot": f"{repeat}:{case['id']}", "repeat": repeat, "case": case}
            for repeat in range(repetitions) for case in spec["cases"]]
