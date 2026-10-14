# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: a Python standard-library read-only server with a dependency-free browser UI, so the dashboard can run beside the existing experiment runner.

## Users

Researchers and developers running controlled Apertus alignment and red-team experiments. They need to inspect a live or completed run without opening a database or copying secrets into a report.

## Product Purpose

The dashboard makes experiment progress and evidence legible: phase, batch activity, inputs, model responses, parser output, judge flags, and transport failures are visible in one place. Success means a reviewer can trace a conclusion back to a specific prompt and response.

## Positioning

It is a read-only evidence viewer for the project's append-only SQLite ledger and external run directories. It does not dispatch models, edit evidence, or promote an automated result to a finding.

## Operating Context

The operator starts a local Python server and points it at a directory containing one or more run directories. The server polls the ledger while a run is active and can also inspect completed runs. Raw evidence remains in its existing location.

## Capabilities and Constraints

- The browser can list runs, filter them, inspect attempts, and expand prompt, response, parsed JSON, judge, and transport details.
- The server uses SQLite read-only connections and handles incomplete, locked, empty, or corrupt stores as visible errors.
- Credentials, environment variables, raw response base64, and absolute host paths must not be rendered or committed.
- The first implementation uses only Python, HTML, CSS, and browser JavaScript with no build step.

## Evidence on Hand

The project has fairness-pair-v1 and three 70B red-team ladder runs, plus batch benchmarks and Docker/CSCS smoke evidence. External run directories are deliberately outside the repository.

## Product Principles

- Evidence before interpretation.
- Read-only by default.
- Progress should be visible without sacrificing raw traceability.
- Errors and unknown states are first-class results.
- Do not turn a clean screen into a claim of universal safety.

## Accessibility & Inclusion

The UI must work with keyboard focus, preserve readable contrast, provide text labels for state indicators, and keep long prompts and responses in scrollable regions instead of clipping them.
