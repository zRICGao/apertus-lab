.PHONY: run
# Starts the Apertus Lab research workbench (API + persistent worker) in Docker.
# Default mode is a mock provider: no model request is sent until a live campaign is started.
# For live runs put LLM_NAME, LLM_BASE_URL and LLM_API_KEY in the repository-root .env.
run:
	cd .. && docker compose -f compose.workbench.yml up --build
