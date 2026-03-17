# Recipe RAG Assistant

A Chinese recipe RAG demo with hybrid retrieval, multi-turn query contextualization, FastAPI service endpoints, and Docker-based deployment.

## Deployment choice

This project is now configured around local `sentence-transformers` embeddings on CPU.

The recommended production path is:

- prepare the model cache on your own machine
- copy the cache to the server
- run the server with local embeddings only

## Install

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

CI uses [requirements-ci.txt](/d:/PythonProject/recipe-rag-assistant/requirements-ci.txt), which keeps the test environment smaller than the full local runtime.

## Environment

Copy `.env.example` to `.env`:

```env
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu
EMBEDDING_LOCAL_FILES_ONLY=true
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## Run

Interactive CLI:

```powershell
python main.py
```

Web service:

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

Logging:

- logs go to both console and `logs/app.log` by default
- `GET /health` returns readiness and basic runtime status

## Docker

Default production compose using local CPU embeddings:

```powershell
docker compose up -d
```

Alternative local compose file:

```powershell
docker compose -f docker-compose.local.yml up -d --build
```

Notes:

- [Dockerfile](/d:/PythonProject/recipe-rag-assistant/Dockerfile) is the fast production app image layered on top of a reusable dependency base image
- [Dockerfile.base](/d:/PythonProject/recipe-rag-assistant/Dockerfile.base) builds the heavy local-embedding runtime layer and should change rarely
- [Dockerfile.full](/d:/PythonProject/recipe-rag-assistant/Dockerfile.full) is the self-contained local build file used by [docker-compose.local.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.local.yml)

## CI/CD

The workflow in [.github/workflows/ci-cd.yml](/d:/PythonProject/recipe-rag-assistant/.github/workflows/ci-cd.yml):

- installs only lightweight test dependencies
- runs unit tests
- only builds and pushes the image when a deploy is explicitly requested
- reuses a dedicated local-embedding base image so deploy-time app image builds stay fast
- the production image is the local-embedding image
- deploys with [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml)

## Files

- [requirements.txt](/d:/PythonProject/recipe-rag-assistant/requirements.txt): base runtime dependencies
- [requirements-local.txt](/d:/PythonProject/recipe-rag-assistant/requirements-local.txt): local embedding extras
- [requirements-dev.txt](/d:/PythonProject/recipe-rag-assistant/requirements-dev.txt): development and test dependencies
- [requirements-ci.txt](/d:/PythonProject/recipe-rag-assistant/requirements-ci.txt): pinned minimal dependencies for GitHub Actions tests
- [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml): default local-embedding production compose
- [docker-compose.local.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.local.yml): local CPU embedding compose
- [docs/deployment.md](/d:/PythonProject/recipe-rag-assistant/docs/deployment.md): deployment details
