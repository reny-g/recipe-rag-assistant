# Recipe RAG Assistant

A Chinese recipe RAG demo with hybrid retrieval, multi-turn query contextualization, FastAPI service endpoints, and Docker-based deployment.

## What changed

The project now supports two embedding deployment modes on CPU:

- `api`: remote embedding API, recommended for production
- `local`: local `sentence-transformers` embedding model, suitable for offline/local deployments

The default production image is now lighter because heavyweight local embedding dependencies are no longer installed unless explicitly requested.

## Install

API embedding runtime only:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Local CPU embedding runtime:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-local.txt
```

Development and tests:

```powershell
pip install -r requirements-dev.txt
```

## Environment

Copy `.env.example` to `.env` and adjust the embedding mode:

```env
EMBEDDING_PROVIDER=api
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu
EMBEDDING_LOCAL_FILES_ONLY=false
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

For local embeddings, switch `EMBEDDING_PROVIDER=local`.

## Run

Interactive CLI:

```powershell
python main.py
```

Web service:

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

Observability:

- logs go to both console and `logs/app.log` by default
- `GET /health` returns readiness and basic runtime status
- `GET /metrics` returns JSON metrics for request counts, latency, sessions, and knowledge base state

## Docker

Lightweight production compose using API embeddings:

```powershell
docker compose up -d
```

Local CPU embedding compose:

```powershell
docker compose -f docker-compose.local.yml up -d --build
```

## CI/CD

The workflow in [.github/workflows/ci-cd.yml](/d:/PythonProject/recipe-rag-assistant/.github/workflows/ci-cd.yml):

- installs `requirements-dev.txt`
- runs unit tests
- verifies the local embedding image still builds in CI
- builds and pushes the lightweight production image to GHCR
- deploys with [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml)

## Files

- [requirements.txt](/d:/PythonProject/recipe-rag-assistant/requirements.txt): lightweight runtime dependencies
- [requirements-local.txt](/d:/PythonProject/recipe-rag-assistant/requirements-local.txt): local embedding extras
- [requirements-dev.txt](/d:/PythonProject/recipe-rag-assistant/requirements-dev.txt): development and test dependencies
- [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml): lightweight production compose
- [docker-compose.local.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.local.yml): local CPU embedding compose
- [docs/deployment.md](/d:/PythonProject/recipe-rag-assistant/docs/deployment.md): deployment details
