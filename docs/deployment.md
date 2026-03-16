# 部署指南

## 当前部署模型

本项目使用单个 FastAPI 进程同时提供后端 API 和演示前端：

- 后端 API：
  - `POST /chat`
  - `POST /chat/stream`
  - `DELETE /sessions/{session_id}`
  - `GET /health`
- 前端：
  - `GET /`
  - `public/assets/` 中的静态资源
  - `public/vendor/` 中的第三方脚本

这意味着当前的部署模型是：

1. 启动一个 FastAPI 服务
2. 暴露端口 `8000`
3. 从 `/` 访问演示页面
4. 页面调用同一个服务的聊天 API

## 本地部署

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

访问：

```text
http://localhost:8000/
```

## Docker 部署

```powershell
docker build -t recipe-rag-assistant .
docker run --rm -p 8000:8000 --env-file .env recipe-rag-assistant
```

## Docker Compose 部署

```powershell
docker compose up -d --build
```

当前 compose 的行为：

- 映射 `8000:8000`
- 读取 `.env` 文件
- 挂载 `data/` 目录
- 挂载 `vector_index/` 目录
- 对 `/health` 进行健康检查

## 服务器部署建议

对于简单的 VM 部署：

1. 安装 Docker 和 Docker Compose
2. 克隆仓库
3. 创建 `.env` 文件
4. 运行 `docker compose up -d --build`
5. 可选：在端口 `8000` 前放置 Nginx 反向代理

## GitHub Actions CI/CD

仓库包含 `.github/workflows/ci-cd.yml`。

### CI 行为

在每次 `push` 和 `pull_request` 时，GitHub Actions 将：

1. 安装依赖
2. 编译 Python 源代码
3. 运行 `pytest tests/unit -q`
4. 构建 Docker 镜像

### 部署行为

有两种部署触发方式：

1. 手动部署：
   - 打开 GitHub Actions
   - 运行 `CI/CD`
   - 设置 `deploy=true`
   - 选择要部署的分支/引用

2. 在提交时显式请求部署：
   - 推送到 `main` 分支
   - 在提交信息中包含 `[deploy]`

示例：

```text
git commit -m "Update prompts and frontend [deploy]"
```

这样可以逐次选择是否部署，而不是每次推送都自动部署。

## 必要的 GitHub Secrets

在使用远程部署前，配置这些仓库密钥：

- `SERVER_HOST`
- `SERVER_PORT`
- `SERVER_USER`
- `SERVER_SSH_KEY`
- `SERVER_APP_DIR`
- `APP_ENV_FILE`

### `APP_ENV_FILE` 示例

将完整的 `.env` 内容作为多行密钥存储：

```env
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HF_ENDPOINT=https://hf-mirror.com
```

## 注意事项

- 当前工作流假设 GitHub 仓库是公开的，以便服务器能通过 HTTPS 进行 `git clone`。
- 如果后来将仓库改为私有，需要将服务器的拉取步骤改为使用部署密钥或 PAT（个人访问令牌）策略。
- 如果你的服务器已经有进程管理器或反向代理，应该将其保留在 Docker 前面，而不是绕过容器设置。
