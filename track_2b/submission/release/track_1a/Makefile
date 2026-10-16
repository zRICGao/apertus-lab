IMAGE ?= apertus-lab-mvp
OUTPUT ?= $(CURDIR)/output
# Also support invoking this Makefile directly from the repository root context.
-include ../../../.env
LLM_NAME ?= swiss-ai/Apertus-v1.5-70B
LLM_BASE_URL ?= https://api.inference.cscs.ch/v1
EXPERIMENT_ID ?= auto
export EXPERIMENT_ID
export LLM_NAME LLM_BASE_URL LLM_API_KEY

ifeq ($(strip $(LLM_API_KEY)),)
$(error Set LLM_API_KEY in the environment before running make run)
endif

.PHONY: run
run:
	docker build -t $(IMAGE) .
	docker run --rm --init -e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY -e EXPERIMENT_ID --mount "type=bind,source=$(CURDIR)/data,target=/app/data,readonly" --mount "type=bind,source=$(OUTPUT),target=/output" $(IMAGE)
