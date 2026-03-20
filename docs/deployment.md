# 部署说明

## 部署模式

本项目采用本地 `sentence-transformers` 嵌入模型在 CPU 上进行部署。

建议流程：

1. 在自有机器上下载嵌入模型
2. 将 Hugging Face 缓存复制到服务器
3. 使用 `EMBEDDING_PROVIDER=local` 启动服务
4. 保持 `EMBEDDING_LOCAL_FILES_ONLY=true`，以确保服务器不会尝试在线获取模型

## 环境变量

核心运行变量：

```env
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu
EMBEDDING_LOCAL_FILES_ONLY=true
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

说明：

- 设置 `EMBEDDING_PROVIDER=local`。
- `EMBEDDING_DEVICE` 在本项目中应保持为 `cpu`。
- `EMBEDDING_LOCAL_FILES_ONLY=true` 假设模型缓存已复制到服务器。
- `LOG_DIR`、`LOG_FILENAME`、`LOG_LEVEL`、`LOG_MAX_BYTES` 和 `LOG_BACKUP_COUNT` 控制文件日志记录。

## 默认生产环境 Compose

使用默认的 [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml)。

特点：

- 使用推送到服务器端注册表的镜像
- 使用本地 CPU 嵌入
- 挂载 `./logs:/app/logs` 以实现持久化文件日志
- 挂载 `./model_cache:/opt/huggingface`
- 适用于 CI/CD 部署到 CPU 服务器

启动命令：

```bash
docker compose up -d
```

## 备用本地 Compose

使用 [docker-compose.local.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.local.yml)。

特点：

- 从 [Dockerfile](/d:/PythonProject/recipe-rag-assistant/Dockerfile) 构建完整的本地嵌入镜像
- 保持项目在 CPU 上运行
- 挂载 `./logs:/app/logs` 以实现持久化文件日志
- 挂载 `./model_cache:/opt/huggingface`
- 适用于本地/脱机嵌入部署

启动命令：

```bash
docker compose -f docker-compose.local.yml up -d --build
```

## CI/CD 行为

位于 [.github/workflows/ci-cd.yml](/d:/PythonProject/recipe-rag-assistant/.github/workflows/ci-cd.yml) 的 GitHub Actions 工作流现在执行以下操作：

1. 安装轻量级测试依赖
   具体来自 [requirements-ci.txt](/d:/PythonProject/recipe-rag-assistant/requirements-ci.txt)
2. 运行单元测试
3. 取消同一分支上其他正在进行的运行
4. 仅在明确请求部署时才构建并推送镜像
5. 将完整的本地嵌入镜像推送到服务器端注册表
6. 使用默认的本地嵌入 [docker-compose.yml](/d:/PythonProject/recipe-rag-assistant/docker-compose.yml) 进行部署

## 为什么流水线现在更快了

- 单元测试运行不再构建应用程序镜像
- 镜像构建和推送不再在每次推送或拉取请求时运行
- CI 中启用了 pip 缓存
- CI 使用固定的最小依赖项集，而不是每次运行都解析整个运行时堆栈
- 自动取消旧的正在进行的运行
- 删除了完整镜像的 GitHub Actions cache 导出，以避免数小时的缓存上传

## 日志记录与监控

服务现在同时写入：

- 用于容器和进程日志的 stdout/stderr
- 用于滚动文件日志的 `LOG_DIR/LOG_FILENAME`

默认文件目标：

```text
/app/logs/app.log
```

API 还公开了：

- `GET /health`：就绪性以及基本运行时状态

## 部署与优化经验总结

### 1. 先定位真正的慢点，再决定怎么优化

这次排查里，拖慢流水线的对象并不固定，先后出现过几种不同瓶颈：

- 测试阶段安装了不必要的重依赖
- 镜像构建后又把完整大镜像导出到 GitHub Actions Cache
- 服务器跨公网拉取大镜像
- 触发规则不清晰，导致为了验证流程反复推送

因此，优化顺序应该是：

1. 先看 Actions 日志里具体慢在哪个 step
2. 判断它是“计算慢”还是“网络传输慢”
3. 再决定是改 Dockerfile、改缓存，还是改镜像分发路径

对本项目来说，后期最慢的部分并不是 Python 代码本身，而是大镜像的缓存导出和远程分发。

### 2. 多阶段构建是对的，但必须配合正确的分发路径

这次实践说明，多阶段构建本身没有问题，它的价值主要在于：

- 把依赖安装和应用代码复制拆开
- 提高依赖层复用概率
- 减少应用代码变动时的无效重装

但多阶段构建只有在下面条件满足时，收益才会真正体现出来：

- 依赖层相对稳定
- 构建缓存能被复用
- 镜像推送和拉取路径不会把整套大层重新传一遍

如果后续流程又把完整镜像重新做一次大规模缓存导出，或者服务器仍然跨公网拉整镜像，那么多阶段构建的收益会被抵消。

结论不是“多阶段构建没用”，而是：

- Dockerfile 分层只是前提
- 镜像缓存策略和分发路径决定了它最终是否真的省时间

### 3. 缓存不是越多越好，重镜像场景下要谨慎

这次最重要的经验之一是：对大镜像启用 `cache-to: type=gha,mode=max` 不一定提速，反而可能明显拖慢。

原因是：

- 本项目使用本地 CPU embedding，镜像层较大
- `cache-to: type=gha,mode=max` 会把完整构建缓存上传到 GitHub Actions Cache
- 对大层来说，这个上传过程本身就可能耗掉大量时间

实际效果是：

- Docker 构建已经完成
- 流水线却继续长时间卡在 `exporting to GitHub Actions Cache`

因此，这次最终保留的经验是：

- 可以保留 `cache-from`
- 但不要默认对完整本地 embedding 镜像启用 `cache-to: type=gha,mode=max`

对于这种镜像体积较大的项目，缓存策略必须看“导出缓存的成本是否真的低于节省下来的构建时间”。

### 3.1 `cache-from` 和 `cache-to` 是什么

在 `docker/build-push-action` 里，这两个参数都和 BuildKit 缓存有关，但作用方向不同：

- `cache-from`
  - 表示“构建时可以从哪里读取已有缓存”
  - 目标是复用之前已经构建过的 layer，减少重复安装依赖、重复复制文件、重复执行构建步骤

- `cache-to`
  - 表示“这次构建完成后，要把新产生的缓存写到哪里”
  - 目标是让后续构建可以继续复用本次结果

如果把它们类比成日常操作：

- `cache-from` 像是“先看看仓库里有没有现成零件可直接拿来用”
- `cache-to` 像是“这次新做好的零件要不要再存回仓库，供下次复用”

本项目曾使用：

```yaml
cache-from: type=gha,scope=server-registry-image
cache-to: type=gha,mode=max,scope=server-registry-image
```

这里的 `type=gha` 表示缓存存到 GitHub Actions 提供的缓存后端。

含义分别是：

- `cache-from: type=gha`
  - 本次构建先去 GitHub Actions Cache 看有没有可复用 layer

- `cache-to: type=gha`
  - 本次构建结束后，把新的 layer 再上传到 GitHub Actions Cache

- `mode=max`
  - 尽可能导出更多缓存内容
  - 命中率更高，但导出体积和耗时也通常更大

### 3.2 为什么这个项目保留 `cache-from`，去掉 `cache-to`

这次实践里，`cache-from` 和 `cache-to` 的收益并不对称。

保留 `cache-from` 的原因：

- 如果 GitHub Actions 上已经有可复用缓存，构建时可以直接命中
- 对依赖层稳定的步骤，理论上仍然可能节省时间
- 读取缓存通常比重新生成缓存的代价更低

去掉 `cache-to` 的原因：

- 本项目镜像较大，包含本地 embedding 相关依赖
- `cache-to: type=gha,mode=max` 会把大量 layer 上传到 GitHub Actions Cache
- 实际观察到的慢点，正是卡在缓存导出，而不是卡在 Dockerfile 本身

所以这次的收敛策略是：

- 可以尝试读取已有缓存
- 但不再默认把完整大镜像缓存重新上传回 GitHub Actions

对于本项目这种“镜像较大、部署链路重、网络传输成本高”的场景，这个取舍更务实。

### 4. 测试链路和部署链路应该拆开考虑

这次提速最明显的部分，实际上来自“不要让所有 push 都走完整部署链路”。

当前更合理的拆分方式是：

- 普通 `push` / `pull_request`：只跑轻量测试
- 明确需要发布时：才构建镜像并部署

具体做法包括：

- 测试 job 只安装 [requirements-ci.txt](/d:/PythonProject/recipe-rag-assistant/requirements-ci.txt) 中的最小依赖
- 普通提交不默认 build / push / deploy
- 只有显式 deploy 时才进入镜像构建与发布流程

这让 CI 的职责更清晰：

- CI 负责快速反馈代码质量
- Deploy 负责分发重镜像并完成上线

不要把两者绑死，否则每次普通开发提交都要为部署链路买单。

### 5. 服务器本地 registry 比“先推远端再回拉”更适合当前项目

本项目当前是：

- 本地 embedding
- CPU 部署
- 单机服务器
- 镜像相对较大

在这个约束下，实践结果说明：

- `Runner -> GHCR -> Server pull` 更依赖公网链路，整体更慢
- `Runner -> 服务器本地 registry -> 服务器本机 pull` 更短、更稳定

所以现在保留下来的部署路径是：

1. GitHub Actions runner 构建镜像
2. runner 直接把镜像推到服务器上的本地 registry
3. 服务器从 `127.0.0.1:5000` 拉取同一个镜像并启动

这条路径的核心收益是：把最慢的一段跨公网镜像分发，替换成服务器本机拉取。

### 6. HTTP registry 需要显式按 insecure registry 处理

这次还踩到了一个很典型但容易忽略的问题：

- 服务器本地 registry 是 `HTTP`
- Docker / Buildx 默认按 `HTTPS` 访问 registry

如果不显式声明 insecure registry，就会出现类似报错：

```text
server gave HTTP response to HTTPS client
```

因此，runner 侧需要同时处理两件事：

- Docker daemon 要把 `${SERVER_HOST}:5000` 视为 insecure registry
- Buildx / BuildKit 也要按 `http=true`、`insecure=true` 配置该 registry

这是使用私有 HTTP registry 时的必要前提，不是可选优化项。

### 7. 触发规则必须和使用方式对齐

当前 workflow 忽略了：

- `README.md`
- `docs/**`

这能减少无意义 CI，但也意味着：

- 仅改文档不会触发 `push`
- 空提交也未必能触发预期流程

因此实际使用时，应该明确采用下面两种方式之一：

- 使用 `workflow_dispatch` 手动触发发布
- 提交非忽略文件，并在提交信息中带 `[deploy]`

触发规则不是“小细节”，它直接决定了发布流程是否可预测。

### 8. 本地先做静态验证，减少无谓试错

虽然当前本地开发环境没有 Docker，无法完整模拟：

- `docker login`
- `docker buildx build --push`
- runner 与 registry 的真实网络联通

但仍然可以在推送前做两类重要验证：

- Python 单测
- workflow 文本、变量引用、条件表达式和文件改动范围的静态检查

这一步不能替代真实部署，但可以明显减少那种“明显写错了还要等流水线报错”的低级试错。

建议固定执行：

```powershell
conda run -n cookbook-rag python -m pytest tests/unit -q
```

### 9. 最终收敛下来的通用策略

这次折腾之后，真正值得保留的经验不是某一条临时 workaround，而是一套更稳定的思路：

1. 让测试链路尽量轻
2. 让部署链路显式触发
3. 用多阶段构建减少无效重装
4. 对大镜像谨慎使用远程缓存导出
5. 优先缩短镜像分发路径，而不是一味堆缓存
6. 使用服务器本地 registry 时，显式处理 HTTP/insecure 配置
7. 推送前先做本地静态验证，减少 CI 试错成本

对本项目这类“CPU + 本地 embedding + 单机部署”的场景来说，这套策略比一味追求复杂缓存或远程构建技巧更稳妥，也更容易长期维护。
