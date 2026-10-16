.PHONY: run run-legacy lab sync lab-status wiki agent-status workbench workbench-demo workbench-test
# Starts the Apertus Lab research workbench (API + persistent worker) in Docker.
# Default mode is a mock provider: no model request is sent until a live campaign is started.
# For live runs put LLM_NAME, LLM_BASE_URL and LLM_API_KEY in track_2b/.env (ignored by Git).
-include .env
export LLM_NAME LLM_BASE_URL LLM_API_KEY

PYTHON ?= python

run:
	docker compose -f compose.workbench.yml up --build

run-legacy:
	$(MAKE) -C submission/release/track_1a run

lab:
	$(PYTHON) scripts/lab.py serve

sync:
	$(PYTHON) scripts/lab.py sync

lab-status:
	$(PYTHON) scripts/lab.py status

wiki:
	$(PYTHON) scripts/wiki-local.py

agent-status:
	$(PYTHON) scripts/agent.py

workbench:
	$(PYTHON) src/workbench.py serve

workbench-demo:
	$(PYTHON) src/workbench.py demo

workbench-test:
	$(PYTHON) scripts/test-workbench.py
