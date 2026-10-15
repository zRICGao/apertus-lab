run:
	docker build -t apertus-replay .
	docker run --rm -e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY -v "$(CURDIR)/output:/output" apertus-replay --live
