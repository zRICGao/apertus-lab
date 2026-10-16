FROM node:24-alpine@sha256:44fce696f38ba8c987c4db89954051000bbd05ffd8d8659ba15ed4a8602e937f AS ui
WORKDIR /ui
COPY src/research-ui/package*.json ./
RUN npm ci
COPY src/research-ui/ ./
RUN npm run build

FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
WORKDIR /app
COPY requirements-workbench.lock.txt ./
RUN pip install --no-cache-dir -r requirements-workbench.lock.txt
COPY src/apertus_lab/ src/apertus_lab/
COPY src/workbench.py src/workbench.py
COPY --from=ui /ui/dist/ src/research-ui/dist/
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 WORKBENCH_DATA=/data WORKBENCH_WIKI=/wiki
ENTRYPOINT ["python","src/workbench.py"]
CMD ["serve","--external-worker","--host","0.0.0.0"]
