# Deployment

## Deployment mode

This project is deployed with local `sentence-transformers` embeddings on CPU.

Recommended process:

1. download the embedding model on your own machine
2. copy the Hugging Face cache to the server
3. start the service with `EMBEDDING_PROVIDER=local`
4. keep `EMBEDDING_LOCAL_FILES_ONLY=true` so the server does not try to fetch models online

## Environment variables

Core runtime variables:

```env
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu
EMBEDDING_LOCAL_FILES_ONLY=true
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Notes:

- Set `EMBEDDING_PROVIDER=local`.
- `EMBEDDING_DEVICE` should stay `cpu` for this project.
- `EMBEDDING_LOCAL_FILES_ONLY=true` assumes the model cache has already been copied to the server.
- `LOG_DIR`, `LOG_FILENAME`, `LOG_LEVEL`, `LOG_MAX_BYTES`, and `LOG_BACKUP_COUNT` control file logging.

## Default production Compose

Use the default [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml).

Characteristics:

- uses the prebuilt GHCR image
- uses local CPU embeddings
- mounts `./logs:/app/logs` for persistent file logs
- mounts `./model_cache:/opt/huggingface`
- suitable for CI/CD deployment to a CPU server

Start it with:

```bash
docker compose up -d
```

## Alternate local Compose

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

1. installs lightweight test dependencies
2. runs unit tests
3. only builds and pushes the image when deploy is explicitly requested
4. deploys with the default local-embedding [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml)

## Why the pipeline is faster now

- unit-test runs no longer build the application image
- image build and push no longer run on every push or pull request
- pip caching is enabled in CI

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
