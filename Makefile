.PHONY: run run-legacy lab sync lab-status wiki agent-status workbench workbench-demo workbench-test
# Keep local credentials in the ignored repository-root .env file.
-include .env
export LLM_NAME LLM_BASE_URL LLM_API_KEY

PYTHON ?= python
run:
	$(MAKE) -C track_2b run

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
	$(PYTHON) track_2b/src/workbench.py serve

workbench-demo:
	$(PYTHON) track_2b/src/workbench.py demo

workbench-test:
	$(PYTHON) scripts/test-workbench.py
