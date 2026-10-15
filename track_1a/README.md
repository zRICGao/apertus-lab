# Frozen Apertus replay

`make run` (from the repository root) replays the frozen cases in `data/frozen.json` against the
model in `LLM_NAME` via `LLM_BASE_URL` / `LLM_API_KEY`, using only target requests at temperature 0.
It never reruns discovery and reports every control and probe row.

- `data/frozen.json` - the two frozen matched cases (matched identity, position reversal), 16 requests.
- `data/matched_identity_campaign/`, `data/position_reversal_campaign/` - original discovery evidence
  (attempts, frozen case, evidence incl. call ids) of the two campaigns. The files directly in `data/`
  are those of the first campaign.
- `findings/finding-01-authority-note-gender.json` - the submitted finding (official schema).
- `technical_report.md` - report source; the PDF is `../TeamName_Report.pdf`.

Scope: hosted service, frozen Chinese prompts and JSON output protocol. See the report for limitations.
