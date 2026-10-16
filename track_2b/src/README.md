# Source layout

| Path | Contents |
|---|---|
| `apertus_lab/platform/` | Workbench: FastAPI app, persistent worker, evidence store, judge, replay, export, Probe |
| `apertus_lab/` (other modules) | Earlier MVP runner, live transport and CLI used by the replay package and legacy tools |
| `research-ui/` | React / TypeScript bilingual interface (Vite) |
| `workbench.py` | Entry point: `serve`, `worker`, `demo` |
| `tests/` | Platform and Probe tests (`python -m unittest discover -s src/tests`) |
| `pyproject.toml` | Package metadata for `apertus_lab` |

The container build is `Dockerfile` and `compose.workbench.yml` in `track_2b/`; `make run` starts it.
Older MVP tests and example specs remain in `experiments/tests` and `experiments/examples`.
