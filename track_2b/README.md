# Apertus Lab — Track 2B

A bounded research workbench for evidence-based, multilingual red-teaming of Apertus.
It runs matched-pair experiments (control vs. probe) against an Apertus endpoint, keeps every raw
request and response in an append-only ledger, applies a rule-based judge, requires human review
before anything becomes a finding, and exports an independent replay package.

Run from the repository root: `make run`, then open http://127.0.0.1:8770.
Start with the default mock mode (no model requests); live mode needs `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`.

- `technical_report.md` — architecture, deployment, evaluation, limitations.
- `Apertus_Lab_Report.pdf` — the same report as PDF.
- `src/README.md` — where the code lives. `docs/ARCHITECTURE.md` — deployment architecture.
