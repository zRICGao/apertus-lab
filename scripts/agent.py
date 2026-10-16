"""Read-only research Agent configuration preflight; no model invocation."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "experiments/examples/basic-config.json"
EXPECTED_MODEL = "swiss-ai/Apertus-v1.5-70B"
EXPECTED_ENDPOINT = "https://api.inference.cscs.ch/v1"


def _keys(value: object, expected: set[str], section: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"Invalid {section} fields")
    return value


def _bounded(value: object, low: int, high: int, name: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"Invalid {name}")


def inspect(config_path: Path, environ: dict[str, str] | None = None) -> dict:
    env = os.environ if environ is None else environ
    raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if raw.get("schema_version") == "BASIC-1":
        sys.path.insert(0, str(ROOT / "track_2b/src"))
        from apertus_lab.basic_contracts import validate_config
        data = validate_config(raw)
        return {"configuration_valid": True, "profile": "BASIC-1", "mode": data["mode"],
                "automation_implemented": True, "live_verified": False,
                "generator_and_target": EXPECTED_MODEL, "fresh_conversation_per_call": True,
                "credentials_present": bool(env.get("LLM_API_KEY")), "limits": data["limits"],
                "entrypoint": "python scripts/explore.py", "official_finding_promotion": False}
    data = _keys(raw,
                 {"schema_version", "enabled", "research_model", "target", "scope", "limits", "promotion"}, "root")
    if data["schema_version"] != "1.0" or type(data["enabled"]) is not bool:
        raise ValueError("Unsupported Agent configuration")
    if data["enabled"]:
        raise ValueError("Autonomous Agent execution is not implemented")
    research = _keys(data["research_model"], {"provider", "base_url_env", "model_env", "api_key_env"}, "research_model")
    target = _keys(data["target"], {"model", "endpoint", "api_key_env"}, "target")
    scope = _keys(data["scope"], {"target_ids", "allow_external_assets", "allow_publication"}, "scope")
    limits = _keys(data["limits"], {"max_cycles", "max_candidates_per_cycle", "max_target_calls_per_cycle",
                                    "max_research_calls_per_cycle", "max_input_chars", "max_output_tokens",
                                    "request_seconds", "cycle_seconds"}, "limits")
    promotion = _keys(data["promotion"], {"candidate_requires_control", "independent_confirmation",
                                            "human_review_for_finding"}, "promotion")
    if research["provider"] != "openai_compatible" or any(
        research[field] != expected for field, expected in {
            "base_url_env": "RESEARCH_LLM_BASE_URL", "model_env": "RESEARCH_LLM_NAME",
            "api_key_env": "RESEARCH_LLM_API_KEY"}.items()
    ):
        raise ValueError("Research model must use dedicated environment variables")
    if target != {"model": EXPECTED_MODEL, "endpoint": EXPECTED_ENDPOINT, "api_key_env": "LLM_API_KEY"}:
        raise ValueError("Target must remain the fixed CSCS Apertus endpoint")
    if scope != {"target_ids": ["cscs-apertus-v1.5-70b"], "allow_external_assets": False,
                 "allow_publication": False}:
        raise ValueError("Target scope must remain restricted")
    if any(promotion.get(k) is not True for k in promotion):
        raise ValueError("Evidence and human review gates are required")
    for name, high in {"max_cycles": 100, "max_candidates_per_cycle": 100,
                       "max_target_calls_per_cycle": 10000, "max_research_calls_per_cycle": 10000,
                       "max_input_chars": 100000, "max_output_tokens": 1024,
                       "request_seconds": 120, "cycle_seconds": 86400}.items():
        _bounded(limits[name], 1, high, name)
    if limits["max_target_calls_per_cycle"] < 3 * limits["max_candidates_per_cycle"]:
        raise ValueError("Target call cap cannot cover candidate controls and replay")
    missing = [name for name in ("RESEARCH_LLM_BASE_URL", "RESEARCH_LLM_NAME", "RESEARCH_LLM_API_KEY",
                              "LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY") if not env.get(name)]
    if env.get("LLM_NAME") and env["LLM_NAME"] != EXPECTED_MODEL:
        raise ValueError("Target model environment differs from fixed target")
    if env.get("LLM_BASE_URL") and env["LLM_BASE_URL"].rstrip("/") != EXPECTED_ENDPOINT:
        raise ValueError("Target endpoint environment differs from fixed target")
    if env.get("RESEARCH_LLM_NAME") and env["RESEARCH_LLM_NAME"] == EXPECTED_MODEL:
        raise ValueError("Research model must be distinct from tested Apertus")
    if env.get("RESEARCH_LLM_API_KEY") and env.get("LLM_API_KEY") and env["RESEARCH_LLM_API_KEY"] == env["LLM_API_KEY"]:
        raise ValueError("Research and target credentials must be distinct")
    return {"configuration_valid": True, "enabled": data["enabled"],
            "credentials_present": not missing, "missing_environment_variables": missing,
            "scope": scope["target_ids"], "limits": limits,
            "automation_implemented": False,
            "next_gate": "Implement and verify planner, tool adapter and evidence workflow before enabling"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect research Agent configuration without network access")
    parser.add_argument("--config", type=Path, default=EXAMPLE)
    args = parser.parse_args()
    try:
        result = inspect(args.config)
    except (ValueError, OSError) as error:
        print(f"Agent configuration invalid: {type(error).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
