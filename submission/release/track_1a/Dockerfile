FROM python:3.12.10-slim-bookworm
WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    LLM_NAME=swiss-ai/Apertus-v1.5-70B \
    LLM_BASE_URL=https://api.inference.cscs.ch/v1
COPY src /app/src
COPY data/spec.json /app/data/spec.json
ENTRYPOINT ["python", "-m", "apertus_lab.reproduce", "--spec", "/app/data/spec.json", "--store", "/output"]
