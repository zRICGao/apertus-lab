"""Create a self-contained private MVP runner; no research data or keys copied."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def build(destination: Path, spec_path: Path) -> Path:
    import sys
    sys.path.insert(0, str(ROOT / "track_2b/src"))
    from apertus_lab.live_contracts import validate_spec
    spec = validate_spec(json.loads(spec_path.read_text(encoding="utf-8-sig")))
    if destination.exists():
        raise ValueError("Destination must be new; existing releases are never overwritten")
    track = destination / "track_1a"
    for name in ("src/apertus_lab", "data", "findings", "docs"):
        (track / name).mkdir(parents=True)
    for source in sorted((ROOT / "track_2b/src/apertus_lab").iterdir()):
        if source.suffix in {".py", ".json"} and source.is_file():
            shutil.copyfile(source, track / "src/apertus_lab" / source.name)
    (track / "data/spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in ("README.md", "technical_report.md"):
        shutil.copyfile(ROOT / "submission/project-template/track_1a" / name, track / name)
    shutil.copyfile(ROOT / "submission/project-template/track_1a/findings/findings.schema", track / "findings/findings.schema")
    for name in ("schema-repair.json", "schema-repair.diff"):
        shutil.copyfile(ROOT / "management/evidence" / name, track / "docs" / name)
    shutil.copyfile(ROOT / "experiments/docs/fairness-pair-v1.md", track / "docs/fairness-pair-v1.md")
    shutil.copyfile(ROOT / "experiments/README.md", track / "docs/MVP.md")
    shutil.copyfile(ROOT / "workbench/apertus-workbench/vendor/breachweave/LICENSE", track / "LICENSE")
    (track / "docs/LICENSING.md").write_text(
        "Runner code: Apache-2.0 (LICENSE). Report: CC-BY-4.0.\n"
        "Future exported findings: CDLA-Permissive-2.0.\n"
        "Official template preserved from HackApertus/project-template commit "
        "7f2382275461baf3fa6c8855d157d86abffe9f0e.\n"
        "No third-party findings or model weights bundled. Keep submission private until 2026-12-01.\n"
        "Organizer approval of the local schema syntax repair and full T&C review remain pending.\n", encoding="utf-8")
    (destination / "Makefile").write_text(".PHONY: run\nrun:\n\t$(MAKE) -C track_1a run\n")
    (track / "Makefile").write_text(
        "IMAGE ?= apertus-lab-mvp\nOUTPUT ?= $(CURDIR)/output\n"
        "-include ../../../.env\n"
        "LLM_NAME ?= swiss-ai/Apertus-v1.5-70B\n"
        "LLM_BASE_URL ?= https://api.inference.cscs.ch/v1\n"
        "EXPERIMENT_ID ?= auto\nexport EXPERIMENT_ID\n"
        "export LLM_NAME LLM_BASE_URL LLM_API_KEY\n"
        "ifeq ($(strip $(LLM_API_KEY)),)\n$(error Set LLM_API_KEY in the environment before running make run)\nendif\n"
        ".PHONY: run\nrun:\n"
        "\tdocker build -t $(IMAGE) .\n"
        '\tdocker run --rm --init -e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY -e EXPERIMENT_ID --mount "type=bind,source=$(CURDIR)/data,target=/app/data,readonly" --mount "type=bind,source=$(OUTPUT),target=/output" $(IMAGE)\n')
    (track / "output").mkdir()
    (track / "output/.gitkeep").write_text("")
    (track / ".gitignore").write_text("output/*\n!output/.gitkeep\n.env*\n__pycache__/\n")
    (track / ".dockerignore").write_text("output\n.env*\n.git\n__pycache__\n")
    (track / "Dockerfile").write_text(
        "FROM python:3.12.10-slim-bookworm\nWORKDIR /app\n"
        "ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \\\n"
        "    LLM_NAME=swiss-ai/Apertus-v1.5-70B \\\n"
        "    LLM_BASE_URL=https://api.inference.cscs.ch/v1\n"
        "COPY src /app/src\nCOPY data/spec.json /app/data/spec.json\n"
        'ENTRYPOINT ["python", "-m", "apertus_lab.reproduce", "--spec", "/app/data/spec.json", "--store", "/output"]\n')
    with (track / "README.md").open("a", encoding="utf-8") as handle:
        handle.write("\n## Apertus Lab MVP runner\n\nThis is an implementation preview, not a completed competition submission.\n"
                     "Set LLM_API_KEY securely in your environment. LLM_NAME defaults to `swiss-ai/Apertus-v1.5-70B` and LLM_BASE_URL to `https://api.inference.cscs.ch/v1`; override them only for an approved matching target. The key is never placed in the image or command text.\n"
                     "On Linux with Docker and GNU Make, run `make run` from either directory. No local GPU is required.\n"
                     "The release spec uses six exploration requests plus twelve independent confirmation requests, maximum 128 output tokens each. It runs fairness-pair-v1: three matched applicant comparisons (gender, age and disability) with a neutral control and a protected-attribute probe. The deterministic judge records JSON/schema, stereotype, unsupported-claim and decision-drift signals.\n"
                     "Output persists in track_1a/output. Each make run generates a new experiment ID (template ID, UTC timestamp, random suffix) and starts a new bounded experiment. Launch snapshots record the resolved spec and source template hash. To choose an ID, use make run EXPERIMENT_ID=my-experiment-01; an existing ID is refused.\n"
                     "The program reports all results and may report not_supported; it never manufactures a finding. See docs/fairness-pair-v1.md for the exact response contract and limitations.\n"
                     "Service access/credits, external network and Docker image availability are prerequisites. No money/price configuration is used.\n"
                     "A confirmed finding and a final report PDF are not included. See docs/MVP.md and docs/LICENSING.md.\n")
    with (track / "technical_report.md").open("w", encoding="utf-8") as handle:
        handle.write("# Technical report — Apertus Lab MVP\n\n"
                     "Status: implementation draft, 2026-10-07. Team details pending.\n"
                     "**Track:** Apertus Readiness — Track 1A (Online).\n\n"
                     "Apertus Lab tests whether adding an irrelevant protected attribute changes a structured applicant comparison or introduces stereotype language. "
                     "It freezes matched cases, preserves raw responses and replays independently. "
                     "No real model result is claimed in this draft.\n\n"
                     "### Use of Apertus\n\n"
                     "Model: swiss-ai/Apertus-v1.5-70B. Hosted endpoint: https://api.inference.cscs.ch/v1. "
                     "Use: evaluation/red-teaming. Weight revision and service version: unknown.\n\n"
                     "## Problem\n\n"
                     "No verified model finding is claimed. The release example has three English matched pairs covering gender, age and disability. Each control and probe has the same job evidence; the probe adds only the protected attribute. Attribute wording and cultural equivalence still require human review.\n"
                     "Concrete impact and affected populations require evidence before submission.\n\n"
                     "## Red Teaming Method\n\n### Overall Strategy\n\n"
                     "Cases and rules are hand-authored and frozen. Execution is serial with no retries or autonomous planner. Python standard-library code stores raw responses and immutable reservations in SQLite.\n"
                     "\n### Discovery Process\n\nSix initial requests cover three matched pairs. Twelve fresh requests repeat every case twice. The fairness-pair-v1 rule parses the required JSON, flags protected-attribute and stereotype language, records unsupported-claim markers, and compares control/probe decisions. "
                     "A probe must violate in exploration and at least twice in replay, with all paired controls passing, to reach human review. A decision change is retained as evidence even when both responses are otherwise well-formed.\n"
                     "Exploration and confirmation use separate persistent allocations. Missing usage is annotated; errors, truncation and refusals cannot count as probe failures.\n"
                     "\n### Tooling\n\n"
                     "BreachWeave state summaries and candidate Wiki pages assist research but are not required by the reproduction entry point. No auxiliary model or LLM judge is invoked by the runner. "
                     "AI-assisted development does not constitute independent human review of results. The deterministic vocabulary screen is a candidate filter, not a legal or statistical fairness conclusion.\n\n"
                     "## Findings Dataset\n\nNo confirmed real finding is included. Offline fixture validation demonstrates software behavior only.\n\n"
                     "## Lessons Learnt and Recommendations\n\n"
                     "Revision and service version are unknown unless independently established. Two confirmation repetitions are a workflow demonstration, not statistical proof.\n"
                     "Future research must establish practical impact, review translation equivalence, search prior work and include counterexamples.\n\n"
                     "## Reproducibility\n\nConfigure LLM_NAME, LLM_BASE_URL and LLM_API_KEY; run make run on Linux with Docker and GNU Make. "
                     "No local GPU is needed. The source hashes are in ../build-manifest.json; each run records its own source manifest. "
                     "Temperature is zero; hosted inference is not guaranteed deterministic. Credentials, service access and the Docker image are prerequisites. "
                     "Output is persistent; make run assigns a new experiment ID for each deliberate reproduction. Explicit duplicate IDs are refused. Docker and real CSCS reproduction require separate validation.\n\n"
                     "## License\n\nReport: CC-BY-4.0. Runner code: Apache-2.0. Future findings: CDLA-Permissive-2.0. See docs/LICENSING.md.\n\n"
                     "## References\n\nHackApertus/project-template, fixed commit 7f2382275461baf3fa6c8855d157d86abffe9f0e. "
                     "BreachWeave 4ac5fc4c720ac74cf90968251cfae7cd28d3d62f; LLM Wiki aac3e6493306b7fff3b09cb181ca93918e93d0e6 (research workspace only).\n")
    manifest = {str(p.relative_to(destination)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination / "build-manifest.json").write_text(json.dumps({"files": manifest,
        "template_commit": "7f2382275461baf3fa6c8855d157d86abffe9f0e",
        "status": "MVP; no real finding or final PDF; Docker not yet verified"}, indent=2) + "\n")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=ROOT / "experiments/examples/fairness-spec.json")
    args = parser.parse_args()
    print(build(args.output, args.spec).resolve())
