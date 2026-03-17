# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder

ARG INSTALL_LOCAL_EMBEDDINGS=false

WORKDIR /install

COPY requirements.txt requirements-local.txt /tmp/

# 这里为runner的/root/.cache/pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r /tmp/requirements.txt && \
    if [ "$INSTALL_LOCAL_EMBEDDINGS" = "true" ]; then \
        pip install --prefix=/install -r /tmp/requirements-local.txt; \
    fi

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface \
    EMBEDDING_DEVICE=cpu

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
