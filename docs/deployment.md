# Deployment Guide

## Current deployment model

This project uses one FastAPI service to serve both the backend APIs and the demo frontend:

- Backend API:
  - `POST /chat`
  - `POST /chat/stream`
  - `DELETE /sessions/{session_id}`
  - `GET /health`
- Frontend:
  - `GET /`
  - static files from `public/assets/`
  - vendor files from `public/vendor/`

That means the current deployment model is:

1. Start one FastAPI service
2. Expose port `8000`
3. Open `/` in the browser
4. Let the page call the same service for chat APIs

## Local deployment

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/
```

## Docker deployment

```powershell
docker build -t recipe-rag-assistant .
docker run --rm -p 8000:8000 --env-file .env recipe-rag-assistant
```

## Docker Compose deployment

```powershell
docker compose up -d --build
```

Current compose behavior:

- maps `8000:8000`
- reads `.env`
- mounts `data/`
- mounts `vector_index/`
- performs a health check on `/health`

## Server deployment recommendation

For a simple VM deployment:

1. Install Docker and Docker Compose
2. Create the target app directory on the server
3. Let GitHub Actions upload the release bundle
4. Let GitHub Actions write `.env`
5. Let GitHub Actions run `docker compose up -d --build`

## GitHub Actions CI/CD

The repo includes `.github/workflows/ci-cd.yml`.

### CI behavior

On every `push` and `pull_request`, GitHub Actions will:

1. install dependencies
2. compile Python sources
3. run `pytest tests/unit -q`
4. build the Docker image

### Deployment behavior

There are two deployment triggers:

1. Manual deploy:
   - open GitHub Actions
   - run `CI/CD`
   - set `deploy=true`
   - choose the ref to deploy

2. Deploy on push when explicitly requested:
   - push to `main` or `master`
   - include `[deploy]` in the commit message

Example:

```text
git commit -m "Fix deployment workflow [deploy]"
```

### Deployment implementation

The deployment job now works like this:

1. checkout the target ref on the GitHub runner
2. create `release.tar.gz`
3. upload the archive to the server with SCP
4. extract the archive into `SERVER_APP_DIR`
5. write `.env` from `APP_ENV_FILE`
6. run `docker compose up -d --build`

This avoids server-side `git clone` and avoids TLS pull failures from GitHub.

## Required GitHub Secrets

Configure these repository secrets before using remote deployment:

- `SERVER_HOST`
- `SERVER_PORT`
- `SERVER_USER`
- `SERVER_SSH_KEY`
- `SERVER_APP_DIR`
- `APP_ENV_FILE`

### `APP_ENV_FILE` example

Store the full `.env` content as one multiline secret:

```env
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HF_ENDPOINT=https://hf-mirror.com
```

## Notes

- The server no longer needs GitHub access for deployment.
- The server only needs Docker, Docker Compose, disk space, and SSH access from GitHub Actions.
- If you already use Nginx or another reverse proxy, keep it in front of the container service.
