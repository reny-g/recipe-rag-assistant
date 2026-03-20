# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder

WORKDIR /install

COPY requirements-local.txt /tmp/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r /tmp/requirements-local.txt

COPY requirements.txt /tmp/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r /tmp/requirements.txt

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface \
    EMBEDDING_DEVICE=cpu

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
