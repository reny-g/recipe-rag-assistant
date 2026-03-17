# Deployment

## Deployment modes

This project now supports two embedding deployment modes:

1. `api`
   Uses a remote embedding API such as DashScope's OpenAI-compatible endpoint.
   This is the recommended production mode because the image is much smaller and does not need local model weights.
2. `local`
   Uses a local `sentence-transformers` embedding model on CPU.
   This is useful when you want fully local embeddings and can accept a heavier image plus model cache.

## Environment variables

Core runtime variables:

```env
EMBEDDING_PROVIDER=api
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu
EMBEDDING_LOCAL_FILES_ONLY=false
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Notes:

- Set `EMBEDDING_PROVIDER=api` for the lightweight production image.
- Set `EMBEDDING_PROVIDER=local` for the local CPU embedding build.
- `EMBEDDING_DEVICE` should stay `cpu` for this project.
- `EMBEDDING_LOCAL_FILES_ONLY=true` is useful only when the local model has already been cached.
- `LOG_DIR`, `LOG_FILENAME`, `LOG_LEVEL`, `LOG_MAX_BYTES`, and `LOG_BACKUP_COUNT` control file logging.

## Lightweight production Compose

Use the default [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml).

Characteristics:

- uses the prebuilt GHCR image
- installs only API embedding runtime dependencies
- mounts `./logs:/app/logs` for persistent file logs
- does not mount Hugging Face model cache
- suitable for CI/CD deployment to a CPU server

Start it with:

```bash
docker compose up -d
```

## Local CPU embedding Compose

Use [docker-compose.local.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.local.yml).

Characteristics:

- builds the image with `INSTALL_LOCAL_EMBEDDINGS=true`
- keeps the project on CPU
- mounts `./logs:/app/logs` for persistent file logs
- mounts `./model_cache:/opt/huggingface`
- suitable for local/offline embedding deployments

Start it with:

```bash
docker compose -f docker-compose.local.yml up -d --build
```

## CI/CD behavior

The GitHub Actions workflow in [.github/workflows/ci-cd.yml](/d:/PythonProject/recipe-rag-assistant/.github/workflows/ci-cd.yml) now does the following:

1. installs `requirements-dev.txt`
2. runs unit tests
3. verifies that the local-embedding image still builds
4. builds and pushes the lightweight production image to GHCR
5. deploys with the default lightweight [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml)

## Why the production image is lighter now

The main reduction comes from moving these packages out of the default runtime image:

- `sentence-transformers`
- `langchain-huggingface`
- `pytest`

These are only installed for local embedding or development/test workflows now.

## Logging and monitoring

The service now writes logs to both:

- stdout/stderr for container and process logs
- `LOG_DIR/LOG_FILENAME` for rotating file logs

Default file target:

```text
/app/logs/app.log
```

The API also exposes:

- `GET /health`: readiness plus basic runtime status
- `GET /metrics`: JSON metrics for request counts, error counts, endpoint latency, sessions, and knowledge-base summary
