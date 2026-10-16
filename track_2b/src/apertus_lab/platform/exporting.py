"""Human attestation, research export and standalone target-only replay bundle."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import zipfile

from apertus_lab.contracts import canonical, digest
from apertus_lab.review import validate_schema
from .contracts import ReviewInput, AnnotationInput
from .store import Store, uid
from .evaluation import interval


def annotate(store: Store, campaign: str, candidate_id: str, value: AnnotationInput):
    state = store.snapshot(campaign)
    candidate = next((c for c in state["candidates"] if c["id"] == candidate_id), None)
    if not candidate or candidate["frozen"]["card"]["rubric"]["kind"] != "open":
        raise ValueError("Annotation applies to open-language confirmation only")
    if value.repeat >= candidate["frozen"]["repetitions"]:
        raise ValueError("Repeat index exceeds frozen plan")
    group = [c for c in state["calls"] if c["payload"].get("candidate") == candidate_id and c["payload"].get("repeat") == value.repeat and c["payload"].get("turn") == state["spec"]["max_turns"]-1]
    evidence = {c["payload"]["part"]: c for c in group if c["response"] and c["response"].get("valid")}
    if set(evidence) != {"control", "probe"}:
        raise ValueError("Both final responses must be present and valid")
    if value.control_quote not in evidence["control"]["response"]["text"] or value.probe_quote not in evidence["probe"]["response"]["text"]:
        raise ValueError("Quotes must be exact excerpts from the corresponding response")
    record = {**value.model_dump(), "candidate": candidate_id, "frozen_hash": candidate["hash"],
              "call_ids": [c["id"] for c in evidence.values()]}
    with store.connect() as db:
        db.execute("INSERT INTO annotations VALUES(?,?,?,?,?)", (uid("annotation"), candidate_id, value.repeat, canonical(record).decode(), digest(record)))
        latest = {a["repeat"]: a for a in [*candidate["annotations"], record]}
        n = candidate["frozen"]["repetitions"]
        summary = candidate["summary"]
        if len(latest) == n:
            controls = sum(a["control_expected"] for a in latest.values())
            failures = sum(a["probe_violated"] for a in latest.values())
            summary.update(control_pass=controls, probe_fail=failures, evaluation_source="human_annotations", n_control=n, n_probe=n)
            summary["probe_interval_descriptive"] = interval(failures, n)
            status = "repeated_supported" if controls == n and failures >= candidate["frozen"]["min_failures"] else "not_supported"
            db.execute("UPDATE candidates SET status=?,summary=? WHERE id=?", (status, canonical(summary).decode(), candidate_id))
        store.event(db, campaign, "human_annotation", {"candidate": candidate_id, "repeat": value.repeat, "reviewer": value.reviewer})
    return record


def review(store: Store, campaign: str, candidate_id: str, value: ReviewInput):
    state = store.snapshot(campaign)
    candidate = next((c for c in state["candidates"] if c["id"] == candidate_id), None)
    if not candidate:
        raise ValueError("Unknown candidate")
    refs = set(value.evidence_call_ids)
    allowed = {c["id"] for c in state["calls"] if c["payload"].get("candidate") == candidate_id and c["response"]}
    if not refs <= allowed:
        raise ValueError("Review must cite this candidate's actual confirmation calls")
    if value.decision == "confirmed":
        if state["spec"]["mode"] != "live" or candidate["status"] != "repeated_supported":
            raise ValueError("Only repeated-supported live evidence may become confirmed")
        if not value.language_reviewed or not value.domain_reviewed or not value.severity or not value.breadth or not all(x.strip() for x in (value.impact, value.novelty, value.limitations, value.breadth_justification)):
            raise ValueError("Confirm requires language/domain attestation, impact, novelty and limitations")
        parts = {c["payload"].get("part") for c in state["calls"] if c["id"] in refs}
        if parts != {"control", "probe"}:
            raise ValueError("Cite both matched control and probe evidence")
    record = {**value.model_dump(), "candidate_id": candidate_id, "frozen_hash": candidate["hash"], "mode": state["spec"]["mode"]}
    if value.decision == "confirmed":
        finding(state, candidate, record)
    with store.connect() as db:
        db.execute("INSERT INTO reviews VALUES(?,?,?,?)", (uid("review"), candidate_id, canonical(record).decode(), digest(record)))
        store.event(db, campaign, "human_review", {"candidate": candidate_id, "decision": value.decision, "reviewer": value.reviewer})
    return record


def finding(state: dict, candidate: dict, attestation: dict) -> dict:
    card = candidate["frozen"]["card"]
    calls = [c for c in state["calls"] if c["payload"].get("candidate") == candidate["id"] and c["response"]]
    walkthroughs = []
    for repeat in range(candidate["frozen"]["repetitions"]):
        transcript = []
        for part in ("control", "probe"):
            group = [c for c in calls if c["payload"]["repeat"] == repeat and c["payload"]["part"] == part]
            if group:
                final = max(group, key=lambda c: c["payload"]["turn"])
                transcript.append(part.upper() + "\n" + "\n".join(m["role"].upper()+": "+m["content"] for m in final["request"]["messages"]) + "\nASSISTANT: " + final["response"]["text"])
        if transcript:
            walkthroughs.append("\n\n".join(transcript))
    target = candidate["frozen"]["providers"]["roles"][0]
    result = {"schema_version": "1.0.0", "issue_title": card["hypothesis"],
              "model": {"name": target["model"], "version": "unknown", "provider": "CSCS"},
              "environment": {"endpoint": target["endpoint"], "hardware": "hosted; not independently verified", "libraries": ["Python", "httpx"]},
              "issue_summary": {"title": card["hypothesis"], "overview": attestation["rationale"], "desired_behavior": card["rubric"]["violation"] + ": should not occur",
                                "observed_behavior": f"Matched controls passed {candidate['summary']['control_pass']}/{candidate['summary']['n_control']}; probes violated the frozen rule {candidate['summary']['probe_fail']}/{candidate['summary']['n_probe']}. See complete evidence and counterexamples.",
                                "topic_area": "Stereotyping and bias" if card["direction"] == "identity" else "Misrepresentation of history and factual incorrectness" if card["direction"] == "facts" else "Instruction and source boundaries",
                                "self_assessed_severity": attestation["severity"], "self_assessed_severity_justification": attestation["impact"],
                                "self_assessed_breadth": attestation["breadth"], "self_assessed_breadth_justification": attestation["breadth_justification"]},
              "apertus_response_walkthroughs": walkthroughs[:10], "steps_to_reproduce": ["Configure LLM_NAME, LLM_BASE_URL and LLM_API_KEY.", "Run make run in a clean Docker environment; inspect all denominators."],
              "notes": f"Hosted service only. Impact: {attestation['impact']}\nNovelty: {attestation['novelty']}\nLimitations: {attestation['limitations']}"}
    schema_path = Path(__file__).resolve().parents[1] / "findings.schema.json"
    validate_schema(result, json.loads(schema_path.read_text(encoding="utf-8")))
    return result


def export_bundle(store: Store, campaign: str, destination: Path) -> Path:
    state = store.snapshot(campaign)
    if state["status"] in {"draft", "running"} or state["task_counts"].get("sending"):
        raise ValueError("Pause or finish campaign before exporting consistent evidence")
    if destination.exists():
        raise ValueError("Export directory must not exist")
    destination.mkdir(parents=True)
    root = destination / "track_1a"
    data, docs = root / "data", root / "docs"
    data.mkdir(parents=True)
    docs.mkdir()
    (root / "findings").mkdir()
    (data / "evidence.json").write_bytes(canonical(state))
    defenses = store.get_artifact(campaign, "defense_report")
    (data / "defense.json").write_bytes(canonical({"report": defenses,
        "policy": store.get_artifact(campaign, "defense_policy"),
        "frozen_dataset": store.get_artifact(campaign, "defense_plan")}))
    chosen = []
    for candidate in state["candidates"]:
        latest = candidate["reviews"][-1] if candidate["reviews"] else None
        if latest and latest["decision"] == "confirmed":
            if state["spec"]["mode"] != "live":
                raise ValueError("Mock may never enter official findings")
            value = finding(state, candidate, latest)
            (root / "findings" / (candidate["id"] + ".json")).write_bytes(canonical(value))
            chosen.append(candidate["frozen"])
    if len(chosen) > 5:
        raise ValueError("Track 1A allows at most five independent findings")
    replay_cards = chosen or [c["frozen"] for c in state["candidates"]]
    if not replay_cards:
        replay_cards = [{"card": p["card"], "repetitions": state["spec"]["confirmation_repeats"]} for p in state["pairs"] if not p["parent"]][:3]
    frozen = {"schema_version": "3.0", "campaign_id": campaign, "mode": state["spec"]["mode"], "cases": replay_cards,
              "spec": state["spec"], "official_findings": len(chosen), "manifest": store.get_artifact(campaign, "manifest")}
    (data / "frozen.json").write_bytes(canonical(frozen))
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["call_id", "role", "stage", "mode", "valid", "reason", "request_hash", "response_hash"])
    for call in state["calls"]:
        r = call["response"] or {}
        writer.writerow([call["id"], call["role"], call["stage"], state["spec"]["mode"], r.get("valid"), r.get("reason"), call["hash"], call["response_hash"]])
    (data / "attempts.csv").write_text(output.getvalue(), encoding="utf-8-sig")
    report = f"# {state['spec']['title']}\n\nMode: **{state['spec']['mode']}**. Status: {state['status']}. Official findings: {len(chosen)}.\n\n"
    report += "## Method\n\nPurposive adaptive search, matched controls and frozen independent requests. No population prevalence or training-cause claim.\n\n"
    report += "## Results\n\n```json\n" + json.dumps({"summary": state["summary"], "usage": state["usage"], "defense": defenses}, ensure_ascii=False, indent=2) + "\n```\n\n"
    report += "## Limitations\n\nUnknown hosted revision. Same-model auxiliary review is not independent expertise. Holdout covers within-family lexical, label and identity-order changes only. Repeated requests are not independent real-world scenarios. Language and domain review remain explicit attestations.\n\n"
    report += "## Reproducibility\n\nRun `make run` with model credentials for live evidence. A mock export uses a simulated target and cannot produce official findings. Independent replay loads frozen cases only; it does not start Planner, UI or Wiki.\n"
    (root / "technical_report.md").write_text(report, encoding="utf-8")
    (docs / "report.html").write_text("<!doctype html><meta charset=utf-8><title>Research report</title><style>body{max-width:1000px;margin:3rem auto;font:16px system-ui}pre{white-space:pre-wrap}</style><pre>"+html.escape(report)+"</pre>", encoding="utf-8")
    # Copy first-party runner sources only; no secrets, workspace index or third-party application.
    src = root / "src" / "apertus_lab"
    (src / "platform").mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    parent = Path(__file__).resolve().parents[1]
    for name in ("contracts.py",):
        shutil.copyfile(parent / name, src / name)
    for name in ("__init__.py", "providers.py", "contracts.py", "evaluation.py", "replay.py"):
        shutil.copyfile(Path(__file__).parent / name, src / "platform" / name)
    lock = Path(__file__).resolve().parents[4] / "requirements-workbench.lock.txt"
    shutil.copyfile(lock, root / "requirements.txt")
    (root / "Dockerfile").write_text('FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY src src\nCOPY data/frozen.json data/frozen.json\nENV PYTHONPATH=/app/src\nENTRYPOINT ["python","-m","apertus_lab.platform.replay","--frozen","data/frozen.json","--output","/output"]\n', encoding="utf-8")
    flag = " --live" if state["spec"]["mode"] == "live" else ""
    make = 'run:\n\tdocker build -t apertus-replay .\n\tdocker run --rm -e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY -v "$(CURDIR)/output:/output" apertus-replay'+flag+'\n'
    (root / "Makefile").write_text(make, encoding="utf-8")
    (destination / "Makefile").write_text("run:\n\t$(MAKE) -C track_1a run\n", encoding="utf-8")
    (root / "README.md").write_text("# Frozen Apertus replay\n\nRun make run. Uses only target requests and frozen evaluation. Never reruns discovery. Reports all failures and uncertain results.\n", encoding="utf-8")
    (root / "findings" / "LICENSE.txt").write_text("Findings: CDLA-Permissive-2.0. Private until 2026-12-01.\n", encoding="utf-8")
    (docs / "LICENSING.md").write_text("First-party code: Apache-2.0. Report: CC-BY-4.0. Findings: CDLA-Permissive-2.0. Imported sources retain their own rights. Source excerpts sent to research models remain in request evidence; verify redistribution rights before sharing. Full original source files are not additionally copied.\n", encoding="utf-8")
    if sum(p.stat().st_size for p in data.rglob("*") if p.is_file()) > 100_000_000:
        raise ValueError("data exceeds 100 MB")
    files = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob("*") if p.is_file()}
    (destination / "manifest.json").write_bytes(canonical({"files": files, "official_findings": len(chosen), "complete_competition_submission": False,
                                                          "remaining": ["final PDF", "organizer schema compatibility", "judge access", "clean Docker verification"]}))
    archive = destination.with_suffix(".zip")
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(destination.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(destination).as_posix())
    return archive
