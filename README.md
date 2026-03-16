# Recipe RAG Assistant

一个面向中文菜谱知识库的工程化 RAG 演示项目，适合用于面试展示、GitHub 作品集和轻量部署演示。

项目特性：
- 混合检索：FAISS 向量检索 + BM25 + RRF 重排
- 多轮对话：支持 query contextualization
- 元数据过滤：按分类和难度筛选
- 服务化：FastAPI + SSE 流式回答
- 演示页：内置轻量前端，适合直接展示部署效果
- 工程能力：索引持久化、兼容性校验、评估脚本、单元测试

## Demo Preview

启动服务后直接访问：

```text
http://localhost:8000/
```

页面支持：
- 在线提问
- 流式输出
- 会话记忆清空
- 服务状态检查
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

- 不只是一个脚本式聊天 demo，而是包含检索、服务、缓存、评估和部署闭环。
- 把向量索引视为缓存而不是事实来源，复用前会检查与当前文档集是否兼容。
- 把“查询补全”和“最终回答”拆成两类不同的 LLM 调用策略。
- 前端展示页与后端服务共用一个 FastAPI 进程，部署路径简单，适合演示。

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

优点：
- 启动路径最短
- 便于调试
- 可直接展示前端页面和 API

### Option 2: Docker

先准备 `.env`，再执行：

```powershell
docker build -t recipe-rag-assistant .
docker run --rm -p 8000:8000 --env-file .env recipe-rag-assistant
```

适合：
- 单机演示
- 本地部署验证
- 录制项目展示视频

### Option 3: Docker Compose

项目已提供 `docker-compose.yml`：

```powershell
docker compose up --build
```

Compose 默认会：
- 暴露 `8000` 端口
- 挂载本地 `data/`
- 挂载 `vector_index/` 以复用索引
- 读取 `.env`
- 对 `/health` 做健康检查

### Option 4: Cloud VM

如果你要部署到云服务器，推荐最简单的方式：

1. 拉取仓库
2. 配置 `.env`
3. 使用 Docker Compose 启动
4. 用 Nginx 反向代理到 `8000`

可用于：
- GitHub README 截图
- 面试远程演示
- 在线作品集访问

### CI/CD

仓库已添加 GitHub Actions 工作流：

```text
.github/workflows/ci-cd.yml
```

当前行为：

- 每次 `push` 和 `pull_request` 都只跑 CI
- 部署不是默认动作，需要显式触发
- 如果某次 `push` 需要同时部署，在提交信息里加 `[deploy]`
- 如果想手动选择分支和时机，可以在 GitHub Actions 里用 `workflow_dispatch`

详细说明见：

- [docs/deployment.md](/d:/PythonProject/recipe-rag-assistant/docs/deployment.md)

## Evaluation

运行轻量评估：

```powershell
python eval/run_eval.py
python eval/run_eval.py --with-answer
```

评估脚本会输出：
- Top1 命中率
- 任意命中率
- 检索耗时
- 回答耗时
- 失败样例报告

当前评估集覆盖：
- 单轮精确问答
- 多轮上下文追问
- 推荐类问题
- 无答案/应拒答场景

## Tests

```powershell
pytest tests/unit -q
```

当前单元测试覆盖重点：
- 默认配置行为
- 混合检索排序逻辑
- 检索缓存
- 索引兼容性校验

## Interview Talking Points

- 为什么混合检索比单一路径更适合菜谱查询
- 为什么向量索引复用前必须做兼容性校验
- 为什么 query contextualization 应该视为可降级增强步骤
- 为什么缓存检索结果而不缓存最终答案
- 为什么前端展示页和后端 API 放在同一个服务里更利于部署演示

如果你想按结构化话术准备面试，可以直接看：
- [docs/interview-notes.md](/d:/PythonProject/recipe-rag-assistant/docs/interview-notes.md)

## Notes

- 仓库自带 `data/` 下的 Markdown 菜谱文件。
- `vector_index/`、`.env`、缓存目录都已被 `.gitignore` 排除。
- 如果要公开到 GitHub，请不要提交真实 API Key。
