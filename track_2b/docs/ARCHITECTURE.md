# Deployment architecture (Track 2B, mandatory statement)

**Components.** Two containers from one image: `api` (FastAPI + static UI, port 8770 on 127.0.0.1) and `worker`
(durable job runner, at most 10 in-flight model requests). State is one SQLite (WAL) database on a volume.
The only external dependency at runtime is an OpenAI-compatible model endpoint set by `LLM_BASE_URL`.

**c) Sovereign Swiss cloud: used and demonstrated.** Our live runs target Apertus v1.5 70B on the CSCS inference
service (Switzerland). Prompts and responses stay in the local ledger.

**a) On-premise: supported.** The platform has no SaaS dependency. Run both containers on the organisation's own host
and point `LLM_BASE_URL` to an on-premise OpenAI-compatible Apertus server. We did not test a self-hosted Apertus server.

**b) Air-gapped: partially verified.** Mock mode and independent replay of mock evidence need no network. A fully
air-gapped live run would need a local Apertus server inside the same network; this was not tested.
