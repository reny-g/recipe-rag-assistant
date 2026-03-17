# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=ghcr.io/reny-g/recipe-rag-assistant-base:local-cpu-py312
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface \
    EMBEDDING_DEVICE=cpu

WORKDIR /app

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
