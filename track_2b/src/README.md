# Source layout

To avoid duplicating a large code base, the implementation stays in its original locations:

| Path (repository root) | Contents |
|---|---|
| `experiments/src/apertus_lab/platform/` | FastAPI app, persistent worker, evidence store, judge, replay, export, Probe |
| `experiments/tests/` | Offline test suite |
| `workbench/research-ui/` | React / TypeScript bilingual UI |
| `Dockerfile.workbench`, `compose.workbench.yml` | Container build and services (api + worker) |
