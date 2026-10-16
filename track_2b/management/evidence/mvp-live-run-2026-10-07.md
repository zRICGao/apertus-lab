# MVP live run — 2026-10-07

## Execution

The user-provided Windows PowerShell output shows `make run` from the repository root built and started the Docker image successfully. Docker build reported image manifest digest:

`sha256:6c6c337866db741abbab65b6bca2845cd398696c14848b7856d19e5dd3bfbb4e`

Target/spec: CSCS `swiss-ai/Apertus-v1.5-70B`; the fixed English/German/French control/probe demo; exact stripped text evaluator; 6 exploration calls and 12 confirmation calls, with two confirmation repetitions per case.

## Runs and outcome

- Exploration: `run-eb589bee41154e81a50c4ce1102b4ce0` — 6 attempts.
- Confirmation: `run-36ae4ea4ade4440392fe99399debe4ce` — 12 attempts; linked to the exploration run.
- All six exploration cases passed once; all six confirmation cases passed twice. No fail, inconclusive, or error outcomes.
- Summary: `not_supported`; `supported_probe_ids` is empty; independent review is still required for any future candidate. This demonstration produced no finding.

## Persisted records

- Append-only evidence database: `submission/release/track_1a/output/evidence.sqlite3`
  - SHA-256: `C04E55A65532FA9F54E79D6B72E36BBDDA17C5B29F26F53689A9E9F99DE006DB`
  - Database contains 6 exploration and 12 confirmation attempts, plus run manifests and outcomes.
- Summary: `submission/release/track_1a/output/summary-run-36ae4ea4ade4440392fe99399debe4ce.json`
  - SHA-256: `8070E9E56E56276CB80128159F664778B398B21D32CED74DFCA63D12C56976BC`

No API key was placed in the source tree or this management evidence. The demonstration experiment's exploration and confirmation stages are consumed; another run must use a new experiment id and a separately designed hypothesis/spec.
