# Simple Workflow

## 1. Purpose
This repository hosts a lightweight AI Agent MVP with a web chat interface, a FastAPI backend, and an optional Snake easter egg fallback.

## 2. Audience
- Developers extending frontend/backend features.
- Maintainers operating local development and release workflows.
- Product/QA reviewers validating runtime behavior and integration points.

## 3. Inputs/Outputs (Interfaces)
### Architecture map
- `frontend/`: Next.js-based chat UI and static assets.
- `backend/`: FastAPI service, tool wiring, and prompt/tool configuration.
- `easter-eggs/`: archived or optional non-core experiences (including Snake static source).

### Startup prerequisites
- Python 3.10+ (backend runtime)
- Node.js 18+ and npm/pnpm (frontend runtime)
- Access to required model/API credentials via environment variables (project-local `.env` as applicable)


### Local development ports
- Frontend dev server: `http://localhost:3000` (Next.js default)
- Backend API server: `http://localhost:8000` (FastAPI/Uvicorn)
- Frontend API target: set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (defaults to this value).

### API entrypoints
- Backend service root: FastAPI app in `backend/` (run according to backend server command in project scripts).
- Core chat/API routes: exposed by the backend FastAPI router layer in `backend/`.
- Frontend runtime endpoint: Next.js app in `frontend/`, which calls backend chat APIs.

### Runtime behavior output
- Primary output: conversational responses in the web UI.
- Fallback output: if chat request fails due to network issues, UI can offer the Snake easter egg.
  - Runtime copy: `frontend/public/snake/`
  - Archived static version: `easter-eggs/snake-static/`

## 4. Constraints/Policies
- Keep architecture boundaries clear (`frontend` UI, `backend` service/tools, `easter-eggs` optional extras).
- Avoid coupling product-critical behavior to easter-egg components.
- Document any new API surface and environment variables in this README when changed.

## 5. Examples
- **Run local backend**: start FastAPI service from `backend/` using project-defined run command.
- **Run local frontend**: start Next.js dev server from `frontend/`, pointing to local backend API.
- **Network failure path**: intentionally block backend connectivity to verify Snake fallback prompt appears.

## 6. Change log / maintenance notes
- Keep this file synchronized with actual folder layout and runtime entrypoints.
- When adding/removing top-level modules, update the architecture map in the same PR.
- Prefer incremental, dated notes in PR descriptions for operational changes affecting setup.

## 7. Naming conventions
- Use one tool function per file where practical.
- Tool module filenames should mirror the primary function name they implement.
- Avoid catch-all names like `skills.py`, `helpers.py`, or `misc.py` for tool modules.
- Any tool module rename must include corresponding import updates in `backend/tools/__init__.py` and documentation updates in `backend/tools/TOOLS.md`.

## 8. Docker 部署与测试（新手完整指南）

> 目标：在 **Docker** 里同时跑起前后端，并在浏览器完成功能测试。  
> 适合第一次接触 Docker 的同学。

### 8.1 你需要先安装什么
1. 安装 **Docker Desktop**（Windows/macOS）或 Docker Engine（Linux）。
2. 安装后打开终端，验证：
   ```bash
   docker --version
   docker compose version
   ```
3. 确认本机的 `3000` 和 `8000` 端口没被占用。

---

### 8.2 项目里和 Docker 相关的文件
- `backend/Dockerfile`：构建 FastAPI 后端镜像。
- `frontend/Dockerfile`：构建 Next.js 前端镜像。
- `docker-compose.yml`：一条命令同时启动前后端。

---

### 8.3 一次性启动（最推荐）
在仓库根目录执行：

```bash
docker compose up --build
```

说明：
- `--build` 会先构建镜像，再启动容器（第一次会比较慢，正常现象）。
- 启动成功后会持续输出日志，不要关掉终端。

访问：
- 前端：`http://localhost:3000`
- 后端健康检查：`http://localhost:8000/health`

如果 `/health` 返回 `{"status":"ok"}`，说明后端正常。

---

### 8.4 如何做基础测试
1. 打开 `http://localhost:3000`。
2. 在界面里输入你的消息（如有 API Key 输入框，填入可用 key）。
3. 发送一条简单问题（例如“你好”），确认前端可收到返回。
4. 同时观察 `docker compose` 终端日志，确认前后端都没有报错。

---

### 8.5 常用运维命令（建议收藏）

```bash
# 后台启动（不占当前终端）
docker compose up -d --build

# 查看运行状态
docker compose ps

# 查看全部日志
docker compose logs -f

# 只看后端日志
docker compose logs -f backend

# 只看前端日志
docker compose logs -f frontend

# 停止并删除容器
docker compose down

# 停止并删除容器 + 网络 + 数据卷（更彻底）
docker compose down -v
```

---

### 8.6 常见问题排查

#### 问题 1：3000/8000 端口冲突
报错通常类似 `address already in use`。  
处理：
- 关闭占用端口的本机程序；或
- 修改 `docker-compose.yml` 的端口映射（例如改成 `3001:3000`）。

#### 问题 2：前端打不开或白屏
处理顺序：
1. `docker compose ps` 看两个容器是否都 `Up`。
2. `docker compose logs -f frontend` 看 Next.js 是否启动成功。
3. `docker compose logs -f backend` 看后端是否异常退出。

#### 问题 3：前端请求不到后端
本项目默认前端通过 `http://localhost:8000` 调后端（已在 compose 构建参数中设置）。  
若你改过端口，请同步更新 `docker-compose.yml` 中的：
- 前端 `build.args.NEXT_PUBLIC_API_BASE_URL`
- 后端 `ports`

#### 问题 4：依赖拉取慢
- 可重试 `docker compose up --build`。
- 确认 Docker Desktop 使用了可用网络。

---

### 8.7 完整“重置后再测”流程
当环境异常时，建议按下面顺序：

```bash
docker compose down -v
docker compose build --no-cache
docker compose up
```

这会清理旧容器/卷并强制重新构建，适合排查“昨天能跑今天不能跑”的问题。
