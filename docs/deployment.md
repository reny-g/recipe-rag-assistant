# 部署说明

## 当前部署模型

这个项目采用前后端一体化部署方案，由同一个 FastAPI 服务同时提供后端 API 和前端演示页面：

- 后端接口：
  - `POST /chat`
  - `POST /chat/stream`
  - `DELETE /sessions/{session_id}`
  - `GET /health`
- 前端页面：
  - `GET /`
  - 静态资源目录 `public/assets/`
  - 第三方前端依赖目录 `public/vendor/`

也就是说，当前系统的部署方式是：

1. 启动一个 FastAPI 服务
2. 对外暴露 `8000` 端口
3. 浏览器访问 `/`
4. 页面通过同域方式调用聊天接口

## 本地部署

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

访问地址：

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

当前 `docker-compose.yml` 的行为：

- 映射 `8000:8000`
- 读取 `.env`
- 挂载 `data/`
- 挂载 `vector_index/`
- 对 `/health` 做健康检查
- 默认优先使用 `IMAGE_NAME` 指定的镜像
- 本地也保留 `build` 配置，方便开发时直接本机构建

### 为什么第一次构建会很慢

这个项目的依赖里包含 `sentence-transformers` 等较重组件，首次构建镜像时可能会触发：

- 大量 Python 依赖下载
- 较大的二进制 wheel 下载
- Docker 镜像分层构建

所以第一次服务器部署明显慢于后续部署，这属于正常现象。

当前仓库已经做了两层优化：

1. `Dockerfile` 先单独复制 `requirements.txt`，避免代码改动时反复失效依赖层缓存
2. 构建时启用 BuildKit，并对 pip 下载目录做缓存挂载

这意味着：

- 只要 `requirements.txt` 不变，后续构建通常会快很多
- 第二次及之后的部署，速度会明显优于首次部署

### 当前推荐的部署路径

当前工作流已经升级为：

1. GitHub Runner 执行测试
2. GitHub Runner 构建 Docker 镜像
3. GitHub Runner 将镜像推送到 GHCR
4. 服务器只登录 GHCR、拉取镜像并启动容器

这样做的好处是：

- 服务器不再现场下载大量 Python 依赖
- 部署速度明显更稳定
- 服务器带宽压力更小
- 更接近 Java 项目“先构建产物，再部署产物”的思路

### `docker compose` 和 `docker-compose` 的区别

部署时这里有一个很常见的坑：不同服务器上的 Compose 命令可能不一样。

常见有两种写法：

- `docker compose`
- `docker-compose`

它们的关系是：

- `docker compose`
  - 这是 Docker Compose V2 的写法
  - 作为 Docker CLI 的子命令存在
  - 现在官方更推荐这种方式
- `docker-compose`
  - 这是较老的独立命令写法
  - 很多旧服务器、旧教程、旧项目还在使用

所以线上部署时不能想当然地假设服务器一定支持某一种写法。

当前仓库的 GitHub Actions 工作流已经做了兼容处理：

1. 优先尝试 `docker compose`
2. 如果不可用，再尝试 `docker-compose`
3. 两者都不可用时，明确报错退出

如果你在服务器上手动排查，建议先执行：

```bash
docker --version
docker compose version
docker-compose --version
```

看这三个命令的输出，就能快速判断服务器到底装的是哪一种环境。

## 服务器部署建议

如果部署到一台简单的 Linux 云服务器，建议按下面的方式准备：

1. 安装 Docker 和 Docker Compose
2. 在服务器上准备目标目录 `SERVER_APP_DIR`
3. 由 GitHub Actions 上传构建归档包
4. 由 GitHub Actions 写入 `.env`
5. 由 GitHub Actions 执行 `docker compose up -d --build`

建议额外确认以下几点：

1. `SERVER_APP_DIR` 配置为具体项目目录，而不是父目录
   例如：`/home/apps/recipe-rag-assistant`
2. 当前 SSH 用户对 `SERVER_APP_DIR` 有读写权限
3. 当前 SSH 用户可以执行 Docker 命令
4. 服务器磁盘空间足够容纳镜像构建和数据文件

## GitHub Actions CI/CD

仓库内已经提供工作流文件：

```text
.github/workflows/ci-cd.yml
```

### CI 行为

每次 `push` 和 `pull_request` 时，GitHub Actions 会执行：

1. 安装依赖
2. 编译 Python 源码，检查语法错误
3. 运行 `pytest tests/unit -q`
4. 构建 Docker 镜像

### 部署触发方式

当前支持两种部署方式：

1. 手动触发部署
   - 打开 GitHub Actions
   - 选择 `CI/CD`
   - 设置 `deploy=true`
   - 指定要部署的分支或提交

2. 在提交时显式触发部署
   - 推送到 `main` 或 `master`
   - 提交信息里包含 `[deploy]`

示例：

```text
git commit -m "修复部署流程 [deploy]"
```

### 当前部署实现

部署阶段现在不再让服务器自己构建镜像，而是改成：

1. GitHub Runner 检出目标代码
2. GitHub Runner 构建镜像
3. GitHub Runner 将镜像推送到 GHCR
4. 服务器登录 GHCR
5. 服务器拉取本次镜像
6. 根据 `APP_ENV_FILE` 生成 `.env`
7. 执行 `docker compose up -d`

这样可以避免服务器在部署阶段重复下载 Python 依赖，也不需要再现场构建镜像。

补充说明：

- 当前工作流默认使用 GHCR 作为镜像仓库
- 工作流里使用 `GITHUB_TOKEN` 非交互登录 GHCR
- 你不需要手工去 GHCR 网页单独注册或复制额外 token，至少在 GitHub Actions 推送镜像这一步不需要
- 服务器部署时同样通过工作流传入的 `GITHUB_TOKEN` 临时登录 GHCR 拉镜像

## 需要配置的 GitHub Secrets

部署前需要在 GitHub 仓库中配置这些 Secrets：

- `SERVER_HOST`
- `SERVER_PORT`
- `SERVER_USER`
- `SERVER_SSH_KEY`
- `SERVER_APP_DIR`
- `APP_ENV_FILE`

### `APP_ENV_FILE` 示例

将完整 `.env` 内容作为一个多行 Secret 保存，例如：

```env
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HF_ENDPOINT=https://hf-mirror.com
```

## GHCR 说明

当前方案使用 GHCR:

```text
ghcr.io/<github-owner>/recipe-rag-assistant
```

关于认证：

- GitHub Actions 推送 GHCR 镜像时，直接使用仓库自带的 `GITHUB_TOKEN`
- 一般不需要你额外去镜像仓库注册、申请、复制新的 token
- 但工作流需要 `packages: write` 权限

关于服务器拉取：

- 现在的工作流会在部署步骤里临时登录 GHCR
- 然后在服务器上执行 `docker pull`
- 这样即使镜像暂时不是公开的，也能在这次工作流里完成部署

## 注意事项

- 服务器现在不需要再主动访问 GitHub 仓库。
- 服务器只需要具备 Docker、Docker Compose、磁盘空间和 SSH 连接能力。
- 如果服务器前面已经有 Nginx 或其他反向代理，可以继续保留，不需要改成前后端分离部署。
- 如果部署失败，优先检查的不是应用代码，而是服务器环境是否满足：
  - Docker 是否安装
  - `docker compose` / `docker-compose` 是否可用
  - `SERVER_APP_DIR` 是否配置正确
  - SSH 用户是否有目录和 Docker 权限
