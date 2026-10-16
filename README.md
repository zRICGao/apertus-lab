# Apertus Lab

**Hack Apertus 2026 — Track 2B.** The submission lives in [`track_2b/`](track_2b/): code in `track_2b/src/`, the [technical report](track_2b/technical_report.md) and its PDF. From the repository root, `make run` starts the workbench in Docker; then open http://127.0.0.1:8770.

## Parallel research workbench v3 (2026-10-15)

The current development entry point is the [v3 workbench usage and research standard](management/WORKBENCH_V3.md). It includes a bilingual React UI, FastAPI, an independent persistent worker, at most 10 in-flight requests shared across campaigns, 27 research cards in three languages, heuristic variants, frozen confirmation, a four-way defence comparison, human review and an independent Docker replay export. The default mode is mock; starting the service does not call any model.

### Probe interactive testing

Probe is a multilingual red-teaming workflow that runs separately from campaigns. In Settings you can save several OpenAI-compatible models, choose one target model and one assistant model, and design tests in areas such as bias, fairness, false premises, sycophancy, harmful language, privacy and instruction boundaries. The translation step creates a separate job for each selected language. Test, suggestion and analysis calls all show the third-party model, endpoint, language and number of requests in the UI, and are sent only after the user confirms. A failed translation affects only its own language, and a worker restart never resends a call whose outcome is unknown.

```powershell
make workbench
# or
docker compose -f compose.workbench.yml up --build
```

Open `http://127.0.0.1:8770` and go to Probe or Settings. On first start the default Apertus 70B profile is discovered from the ignored root `.env` file; model profiles and the SQLite ledger are stored in `WORKBENCH_DATA`. Keys are used only locally by the backend and never appear in API responses, browser storage, events, record exports or Git. Saved results can be filtered by area and language under Records and exported as JSON or Markdown. "Discard" keeps only immutable audit metadata and does not enter the normal records.

Probe interfaces and state conventions are described in the [Probe v1 workflow](management/PROBE_V1.md). Automatic analysis only organises evidence: it does not create findings, infer training causes, estimate prevalence or draw legal conclusions. Open-ended results still need human review.

```powershell
docker compose -f compose.workbench.yml up --build -d
# with dependencies installed locally: python track_2b/src/workbench.py serve
```

Open http://127.0.0.1:8770 and follow *New study → Preflight → Create → Start*. The full LLM Wiki is started with `python scripts/wiki-local.py` at http://localhost:3000 and shares its knowledge workspace with the workbench. Deployment, role configuration, budgets, detection and human review are covered in the manual above; acceptance results are in the [architecture acceptance record](management/evidence/workbench-v3-acceptance-2026-10-15.md).

The offline and Docker workflows of the platform are complete. Real 10-way parallel runs, research-model quality and domain calibration still need independent validation. The sections below keep the historical usage of the read-only dashboard, the BASIC CLI and the older frozen release package; they do not define the limits of v3. The root `make run` starts the v3 workbench (Track 2B); the older frozen competition package is available as `make run-legacy`.

## Entry points for future developers and AI agents

Read the [product record](PRODUCT.md) first to understand the scope of the dashboard, then [70B red-teaming experience](docs/red-team-experience-70b.md) for the prompts already tried, why they failed, the actual results and the limits of the judge. To inspect real runs, start the [read-only evidence dashboard](dashboard/README.md); it reads SQLite run directories outside the repository, sends no model requests and does not modify the ledger.

Recommended reading order:

1. [Project status and constraints](management/STATUS.md)
2. [Experiment manual](experiments/README.md)
3. [Fairness judge notes](experiments/docs/fairness-pair-v1.md)
4. [70B red-team ladder v1](experiments/docs/redteam-ladder-70b-v1.md), [v2](experiments/docs/redteam-ladder-70b-v2.md), [v3](experiments/docs/redteam-ladder-70b-v3.md)
5. [Red-teaming experience and recommendations](docs/red-team-experience-70b.md)

Real API outputs and local credentials are not part of Git. Read the specs in `experiments/examples/`, the runner and judge in `track_2b/src/apertus_lab/`, the external SQLite evidence and the human reports separately. `not_supported` means the current sample did not support a hypothesis; it is not a general proof of safety.

## BASIC automatic exploration (development version)

Placeholder template generation, automatic topic selection, bounded wording variants, persistent re-testing, stopping rules and human review are connected. The default is offline mock mode. See the [BASIC usage notes](management/BASIC_EXPLORATION.md) for full instructions; the [acceptance record](management/evidence/basic-workflow-2026-10-07.md) contains test results and actual limits.

```powershell
python scripts/explore.py init --config experiments/examples/basic-config.json --store experiments/runs/basic-demo
python scripts/explore.py run --store experiments/runs/basic-demo
```

Real calls need a separate live configuration and an explicit `--live` flag. BASIC candidates carry a placeholder marker and never become formal findings directly. The manual cases and the "no autonomous planner" limit described below refer to the original MVP; the standalone Docker release package keeps its original implementation.

## Local workbench

The current focus is on completing the architecture and debugging with existing evidence. See the [actual architecture](management/ARCHITECTURE.md). From the project root:

```powershell
make sync       # sync existing evidence into Wiki drafts and Memory summaries; no model calls
make lab        # open http://127.0.0.1:8765
```

`make lab-status` checks the ledger and references; `make wiki` calls the full Wiki launcher (API/Web flow pending acceptance). The workbench reads raw evidence only. `make run-legacy` is the standalone Docker experiment entry of the older package: each run generates a new experiment ID and calls the target model; the current template allows at most 6 exploration and 12 confirmation calls per round. Use `make run-legacy EXPERIMENT_ID=my-experiment-01` to set an ID; stages that already exist are still not resent. The ID is shown at start-up, and the actual configuration and template hash are saved in `launch-<run_id>.json` in the output. To recover from an interruption, check the original run ID; a new ID is not a recovery.

Dual-model configuration, preflight and the future automatic loop of the research agent are described in [research agent setup](management/RESEARCH_AGENT_SETUP.md). `make agent-status` checks the non-secret template and environment variables read-only and does not start a model or an experiment.

A text research MVP around CSCS Apertus v1.5 70B: manual cases, serial calls, persistent resource limits, raw evidence, independent re-runs, a candidate Wiki, human confirmation and finding export.

Monetary budgets and exact pricing controls were removed at the user's request. Call counts, input characters, output tokens, time limits and cancellation are still enforced; there are no automatic retries and no autonomous planner.

- [Manual](experiments/README.md): validation, live runs, cancel/resume, Wiki, human confirmation and export.
- [Experiment example](experiments/examples/live-spec.json): three matched English/German/French pairs, 6 exploration and 12 confirmation calls.
- [CSCS access](management/CSCS_API_SETUP.md): configures only the official hosted API; no local model service is needed.
- [Project contract](HARNESS.md) and [current status](management/STATUS.md): separate what is implemented, verified offline, run against the real model and finally delivered.

The MVP runner uses only the Python standard library. The extracted BreachWeave assets are used for task summaries and the full LLM Wiki for research knowledge; neither is part of the independent reproduction entry. The original mock path still works.

With `PYTHONPATH=track_2b/src` set at the project root, `python -m apertus_lab.cli validate-live --spec experiments/examples/live-spec.json` runs an offline check, and `python -m unittest discover -s experiments/tests -v` and `python -m unittest discover -s track_2b/src/tests -v` run the offline tests.

Docker/CSCS connectivity, a batch benchmark, an initial fairness screen and the 70B red-team ladder v1/v2/v3 are complete. The workbench surfaced one reproducible case, described in the [Track 2B technical report](track_2b/technical_report.md); it has had AI-assisted review only, not independent human confirmation. Git contains reproducible code, specs, method documents and redacted summaries, but no real API output ledgers or credentials.
