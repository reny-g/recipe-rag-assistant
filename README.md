# Recipe RAG Assistant

一个面向中文菜谱知识库的工程化 RAG Demo，支持混合检索、多轮对话改写、流式回答，以及基于 Docker 的部署演示。

## Features

- 混合检索：FAISS 向量检索 + BM25 + RRF 融合重排
- 多轮对话：支持 query contextualization
- 元数据过滤：可按分类、难度做检索过滤
- 服务化：FastAPI + SSE 流式输出
- 演示页面：内置轻量前端，便于本地和远程展示
- 工程能力：索引持久化、兼容性校验、评估脚本、单元测试、CI/CD

## Demo

启动服务后访问：

```text
http://localhost:8000/
```

页面支持：

- 在线提问
- 流式输出
- 会话清空
- 服务健康检查
- 示例问题一键填充

## Project Structure

```text
recipe-rag-assistant/
  |- api.py
  |- main.py
  |- config.py
  |- public/
  |- rag/
  |- data/
  |- eval/
  |- scripts/
  |- tests/
  |- Dockerfile
  |- docker-compose.yml
  |- requirements.txt
```

## Architecture

```text
Markdown recipe files
  -> DataPreparation
  -> Markdown-aware chunking
  -> Embeddings + FAISS index
  -> HybridRetriever
     - vector retrieval
     - BM25 retrieval
     - RRF reranking
     - title bonus
  -> RagGenerator
     - query contextualization
     - grounded answer generation
  -> FastAPI
     - REST API
     - SSE streaming
     - static demo page
```

## Why This Project Is Worth Showing

- 不只是一个脚本式聊天 demo，而是包含检索、服务、评估、部署的完整闭环
- 将向量索引视为缓存而不是事实来源，复用前会做兼容性校验
- 将查询补全和最终回答拆成两类不同的 LLM 调用策略
- 前端展示页与后端 API 共用一个 FastAPI 服务，部署路径简单

## Quick Start

### 1. Install

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

从 `.env.example` 复制一份 `.env`：

```env
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HF_ENDPOINT=https://hf-mirror.com
```

### 3. Run interactive CLI

```powershell
python main.py
```

### 4. Run web service

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

然后访问：

```text
http://localhost:8000/
```

## API Examples

### Health check

```bash
curl http://localhost:8000/health
```

### Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"陈皮排骨汤怎么做？\",\"session_id\":\"demo\"}"
```

### Streaming chat

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"陈皮排骨汤怎么做？\",\"session_id\":\"demo\"}"
```

### Clear session

```bash
curl -X DELETE http://localhost:8000/sessions/demo
```

## Deployment

### Option 1: Local process

适合本地开发和面试现场演示。

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Option 2: Docker

```powershell
docker build -t recipe-rag-assistant .
docker run --rm -p 8000:8000 --env-file .env recipe-rag-assistant
```

### Option 3: Docker Compose

```powershell
docker compose up --build
```

### Option 4: Cloud VM

推荐使用 CI 构建镜像、GHCR 存镜像、服务器拉镜像部署。

详细说明见：

- [docs/deployment.md](/d:/PythonProject/recipe-rag-assistant/docs/deployment.md)

## Evaluation

```powershell
python eval/run_eval.py
python eval/run_eval.py --with-answer
```

当前评估覆盖：

- 单轮精确问答
- 多轮上下文追问
- 推荐类问题
- 无答案 / 拒答场景

## Tests

```powershell
pytest tests/unit -q
```

当前单元测试主要覆盖：

- 默认配置行为
- 混合检索排序逻辑
- 检索缓存
- 索引兼容性校验

## Notes

- 仓库自带 `data/` 下的 Markdown 菜谱文件
- `vector_index/`、`.env`、缓存目录都已被 `.gitignore` 排除
- 如果要公开到 GitHub，不要提交真实 API Key
