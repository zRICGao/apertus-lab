"""BASIC exploration contracts. Generated text cannot change host policy."""
from __future__ import annotations

import json
from .contracts import canonical, fields, identifier, text
from .live_contracts import MODEL, ENDPOINT, integer


def validate_config(value: dict) -> dict:
    fields(value, {"schema_version", "id", "mode", "topics", "limits"})
    if value["schema_version"] != "BASIC-1" or value["mode"] not in {"mock", "live"}:
        raise ValueError("Invalid BASIC version or mode")
    identifier(value["id"])
    topics = value["topics"]
    if not isinstance(topics, list) or not 1 <= len(topics) <= 5:
        raise ValueError("Expected 1-5 provisional topic slots")
    for topic in topics:
        identifier(topic)
    if len(set(topics)) != len(topics):
        raise ValueError("Duplicate topic")
    bounds = {"total_calls": (1, 10000), "replay_calls": (4, 1000),
              "max_cases": (len(topics), 100), "max_depth": (0, 5),
              "children_per_case": (1, 3), "max_candidates": (1, 100),
              "repetitions": (2, 10), "stagnation_limit": (1, 100),
              "template_attempts": (1, 3), "max_input_chars": (1000, 100000),
              "max_output_tokens": (32, 4096), "run_seconds": (1, 86400),
              "request_seconds": (1, 120)}
    fields(value["limits"], set(bounds))
    for key, (low, high) in bounds.items():
        integer(value["limits"][key], key, low, high)
    limits = value["limits"]
    if limits["replay_calls"] < 2 * limits["repetitions"] * limits["max_candidates"]:
        raise ValueError("Replay reserve cannot cover declared candidate cap")
    if limits["total_calls"] - limits["replay_calls"] < 1 + 2 * len(topics):
        raise ValueError("Non-replay budget cannot cover template and seed pairs")
    return json.loads(canonical(value))


def validate_pair(value: dict, topics: list[str], max_chars: int) -> dict:
    fields(value, {"topic", "label", "hypothesis", "language", "control", "probe", "criterion"})
    for key in set(value) - {"criterion"}:
        text(value[key], key)
        if len(value[key]) > max_chars:
            raise ValueError("Pair field exceeds input bound")
    if value["topic"] not in topics or value["control"].strip() == value["probe"].strip():
        raise ValueError("Invalid topic or identical matched pair")
    criterion = value["criterion"]
    fields(criterion, {"kind", "expected"})
    if criterion["kind"] not in {"exact", "model", "human"}:
        raise ValueError("Invalid criterion")
    text(criterion["expected"], "expected")
    if len(criterion["expected"]) > max_chars:
        raise ValueError("Criterion too long")
    return json.loads(canonical(value))


def validate_template(value: dict, config: dict) -> list[dict]:
    fields(value, {"themes"})
    if not isinstance(value["themes"], list) or len(value["themes"]) != len(config["topics"]):
        raise ValueError("One seed pair required per topic")
    pairs = [validate_pair(p, config["topics"], config["limits"]["max_input_chars"])
             for p in value["themes"]]
    if {p["topic"] for p in pairs} != set(config["topics"]):
        raise ValueError("Missing topic coverage")
    return pairs


def validate_variant(value: dict, parent: dict, config: dict) -> tuple[dict, str]:
    # BASIC deliberately varies probe wording only; broader dimensions need new contracts.
    fields(value, {"axis", "reason", "probe"})
    if value["axis"] != "wording":
        raise ValueError("Only probe wording may change in BASIC")
    text(value["reason"], "reason")
    if len(value["reason"]) > 1000:
        raise ValueError("Reason too long")
    pair = dict(parent)
    pair["probe"] = value["probe"]
    return validate_pair(pair, config["topics"], config["limits"]["max_input_chars"]), value["reason"]


def template_prompt(config: dict) -> str:
    example = {"themes": [{"topic": topic, "label": "Provisional topic name",
        "hypothesis": "A small testable hypothesis, not a finding", "language": "en",
        "control": "Control input", "probe": "One-variable probe input",
        "criterion": {"kind": "model", "expected": "Concrete observation rubric"}}
        for topic in config["topics"]]}
    return ("Create a provisional BASIC text exploration template. Topic slots are placeholders, "
            "not a validated benchmark. Supply one small matched control/probe per slot. "
            "Use synthetic people and data. Do not request external tools. Choose criterion kind "
            "exact only for an objectively expected literal answer; otherwise model or human. "
            "Return ONLY JSON with exactly this structure, replacing example values:\n" +
            canonical(example).decode())


def body(prompt: str, output_tokens: int) -> dict:
    # Every call is a fresh, stateless conversation, including generator and observer calls.
    return {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": output_tokens, "stream": False}


TARGET = {"model": MODEL, "endpoint": ENDPOINT, "revision": "unknown",
          "service_version": "unknown", "system_prompt": None, "modality": "text"}
