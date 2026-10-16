# Root Make entry verification — 2026-10-07

Observed issue: invoking `make run` from `C:\Users\gaoch\apertus-lab` failed because the repository root had no Makefile. The generated release Makefiles existed below `submission/release/`.

Change: added a root `Makefile` whose `run` target delegates to `submission/release/track_1a`.

Verification: `make -n run LLM_API_KEY=placeholder` expanded through the root target to the expected `docker build` and `docker run` commands, including LLM_* environment passthrough and data/output mounts. The placeholder was used only to satisfy the Makefile's parse-time non-empty guard; dry-run does not invoke Docker or send model requests. No API key value was read or emitted.

Live execution remains unverified until Docker CLI and the real `LLM_API_KEY` are available in the executing PowerShell session.
