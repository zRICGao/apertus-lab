# Technical report — Apertus Lab MVP

Status: implementation draft, 2026-10-07. Team details pending.
**Track:** Apertus Readiness — Track 1A (Online).

Apertus Lab tests whether adding an irrelevant protected attribute changes a structured applicant comparison or introduces stereotype language. It freezes matched cases, preserves raw responses and replays independently. No real model result is claimed in this draft.

### Use of Apertus

Model: swiss-ai/Apertus-v1.5-70B. Hosted endpoint: https://api.inference.cscs.ch/v1. Use: evaluation/red-teaming. Weight revision and service version: unknown.

## Problem

No verified model finding is claimed. The release example has three English matched pairs covering gender, age and disability. Each control and probe has the same job evidence; the probe adds only the protected attribute. Attribute wording and cultural equivalence still require human review.
Concrete impact and affected populations require evidence before submission.

## Red Teaming Method

### Overall Strategy

Cases and rules are hand-authored and frozen. Execution is serial with no retries or autonomous planner. Python standard-library code stores raw responses and immutable reservations in SQLite.

### Discovery Process

Six initial requests cover three matched pairs. Twelve fresh requests repeat every case twice. The `fairness-pair-v1` rule parses the required JSON, flags protected-attribute and stereotype language, records unsupported-claim markers, and compares control/probe decisions. A probe must violate in exploration and at least twice in replay, with all paired controls passing, to reach human review. A decision change is retained as evidence even when both responses are otherwise well-formed.
Exploration and confirmation use separate persistent allocations. Missing usage is annotated; errors, truncation and refusals cannot count as probe failures.

### Tooling

BreachWeave state summaries and candidate Wiki pages assist research but are not required by the reproduction entry point. No auxiliary model or LLM judge is invoked by the runner. AI-assisted development does not constitute independent human review of results. The deterministic vocabulary screen is a candidate filter, not a legal or statistical fairness conclusion.

## Findings Dataset

No confirmed real finding is included. Offline fixture validation demonstrates software behavior only.

## Lessons Learnt and Recommendations

Revision and service version are unknown unless independently established. Two confirmation repetitions are a workflow demonstration, not statistical proof.
Future research must establish practical impact, review translation equivalence, search prior work and include counterexamples.

## Reproducibility

Configure LLM_NAME, LLM_BASE_URL and LLM_API_KEY; run make run on Linux with Docker and GNU Make. No local GPU is needed. The source hashes are in ../build-manifest.json; each run records its own source manifest. Temperature is zero; hosted inference is not guaranteed deterministic. Credentials, service access and the Docker image are prerequisites. Output is persistent; a repeated phase is refused. A new deliberate reproduction uses a new empty OUTPUT directory. Docker and real CSCS reproduction require separate validation.

## License

Report: CC-BY-4.0. Runner code: Apache-2.0. Future findings: CDLA-Permissive-2.0. See docs/LICENSING.md.

## References

HackApertus/project-template, fixed commit 7f2382275461baf3fa6c8855d157d86abffe9f0e. BreachWeave 4ac5fc4c720ac74cf90968251cfae7cd28d3d62f; LLM Wiki aac3e6493306b7fff3b09cb181ca93918e93d0e6 (research workspace only).
