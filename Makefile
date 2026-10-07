.PHONY: run lab sync lab-status wiki agent-status
# Keep local credentials in the ignored repository-root .env file.
-include .env
export LLM_NAME LLM_BASE_URL LLM_API_KEY

PYTHON ?= python
run:
	$(MAKE) -C submission/release/track_1a run

lab:
	$(PYTHON) scripts/lab.py serve

sync:
	$(PYTHON) scripts/lab.py sync

lab-status:
	$(PYTHON) scripts/lab.py status

wiki:
	$(PYTHON) scripts/lab.py wiki

agent-status:
	$(PYTHON) scripts/agent.py
