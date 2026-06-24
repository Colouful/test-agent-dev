# 错题本 — 部署文档

## 公网访问地址

**https://dp2xub6x3xhh2.cloudfront.net**

| 路径 | 说明 |
|------|------|
| `https://dp2xub6x3xhh2.cloudfront.net/` | Vue 3 前端应用 |
| `https://dp2xub6x3xhh2.cloudfront.net/api/v1/` | FastAPI 后端 |
| `https://dp2xub6x3xhh2.cloudfront.net/api/docs` | Swagger 接口文档 |

---

## 架构概览

```
用户浏览器
    │
    ▼
CloudFront (dp2xub6x3xhh2.cloudfront.net)
    │
    ▼
EC2 实例 (100.31.100.88) — Nginx :80
    ├── /api/*  →  FastAPI (uvicorn :8000)
    │               └── SQLite (wrongbook.db)
    │               └── MOCK_BEDROCK=true (本地 mock 识别)
    └── /*      →  Node.js 静态服务器 (:3000)
                    └── Vue 3 SPA (dist/)
```

---

## 快速启动（开发 / 重启）

### 前置条件

```bash
# 在 EC2 实例上（已预置）：
# - Python 3.12 + uv
# - Node.js v22
# - Nginx
```

### 1. 启动后端（FastAPI + uvicorn）

```bash
cd /workshop/ypjh
MOCK_BEDROCK=true /workshop/ypjh/backend/.venv/bin/uvicorn \
  backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  > /tmp/wrongbook-backend.log 2>&1 &

echo "Backend PID: $!"
```

验证：
```bash
curl http://localhost:8000/api/v1/auth/register -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@x.com","password":"pw123"}'
# 期望: {"data":{"access_token":"..."},"error":null}
```

### 2. 编译前端（如有代码变更）

```bash
cd /workshop/ypjh/frontend
npm run build
# 输出到 frontend/dist/
```

### 3. 启动前端静态服务器（Node.js SPA server）

```bash
node /workshop/ypjh/serve-frontend.js > /tmp/wrongbook-frontend.log 2>&1 &
echo "Frontend PID: $!"
```

验证：
```bash
curl http://localhost:3000/
# 期望：HTML containing <title>错题本</title>
```

### 4. 验证 Nginx 路由

```bash
# Nginx 已运行，监听 :80，配置在 /etc/nginx/conf.d/code-editor.conf
# 路由规则：
#   /api/* → localhost:8000  (FastAPI)
#   /code/ → localhost:8080  (VS Code editor)
#   /*     → localhost:3000  (Vue SPA)

sudo nginx -t && sudo nginx -s reload
```

---

## 环境变量

### 后端（`backend/.env.example`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | `change-me-in-production-...` | JWT 签名密钥（**生产必须修改**） |
| `DATABASE_URL` | `sqlite+aiosqlite:///./wrongbook.db` | 数据库连接字符串 |
| `MOCK_BEDROCK` | `true` | `true` = 本地 mock，`false` = 真实 AWS Bedrock |
| `S3_BUCKET` | — | 图片存储桶（MOCK_BEDROCK=false 时需填） |
| `AWS_DEFAULT_REGION` | — | AWS 区域（MOCK_BEDROCK=false 时需填） |

### 前端（`frontend/.env.example`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_MOCK` | `true` | `true` = 用 mock 数据，`false` = 真实后端 |
| `VITE_API_BASE_URL` | `/api` | API 基础路径 |

前端生产构建（`npm run build`）使用 `frontend/.env.production`（`VITE_MOCK=false`）。

---

## Nginx 配置

文件：`/etc/nginx/conf.d/code-editor.conf`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name *.cloudfront.net;

    # FastAPI 后端
    location /api/ {
      proxy_pass http://localhost:8000/api/;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_read_timeout 60s;
    }

    # VS Code 编辑器（/code/ 路径）
    location /code/ {
      proxy_pass http://localhost:8080/;
      proxy_set_header Host $host;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection upgrade;
    }

    # Vue SPA 前端
    location / {
      proxy_pass http://localhost:3000/;
      proxy_set_header Host $host;
    }
}
```

---

## 前端静态服务器

文件：`/workshop/ypjh/serve-frontend.js`

Node.js HTTP 服务，监听 `:3000`，服务 `frontend/dist/`，支持 SPA 路由回退（所有未知路径返回 `index.html`）。

---

## 运行验证（当前状态）

```bash
# 后端测试（75 tests）
cd /workshop/ypjh/backend && uv run pytest tests/ -q
# ✓ 75 passed, 1 warning

# 前端类型检查
cd /workshop/ypjh/frontend && npm run type-check
# ✓ 无错误

# 前端构建
cd /workshop/ypjh/frontend && npm run build
# ✓ built in ~3.6s

# 跨用户隔离（R1）
# Alice 创建题目，Bob 看不到 → total=0 ✓
```

---

## 安全注意事项（生产前必须处理）

| 项目 | 当前状态 | 生产建议 |
|------|---------|---------|
| SECRET_KEY | 固定默认值 | `openssl rand -hex 32` 生成并设为环境变量 |
| HTTPS | 由 CloudFront 终止 | 已由 CloudFront 处理 ✓ |
| 数据库 | SQLite 单文件 | 迁移到 RDS PostgreSQL |
| 图片存储 | MOCK_BEDROCK=true | 生产接入真实 S3 + Bedrock |
| CORS | 允许 localhost:5173 | 生产改为实际域名 |
| 软删除 | 已实现（R21）| 已上线 ✓ |
| 用户隔离 | R1 已验证 | 已上线 ✓ |

---

## 停止服务

```bash
# 停止后端
kill $(pgrep -f "uvicorn backend.main") 2>/dev/null

# 停止前端
kill $(pgrep -f "serve-frontend.js") 2>/dev/null
```

---

## 进程持久化（可选）

如需重启后自动恢复，可用 systemd：

```bash
# /etc/systemd/system/wrongbook-backend.service
[Unit]
Description=错题本 FastAPI Backend
After=network.target

[Service]
User=participant
WorkingDirectory=/workshop/ypjh
Environment=MOCK_BEDROCK=true
ExecStart=/workshop/ypjh/backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# /etc/systemd/system/wrongbook-frontend.service
[Unit]
Description=错题本 Vue SPA Frontend
After=network.target

[Service]
User=participant
ExecStart=/usr/bin/node /workshop/ypjh/serve-frontend.js
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wrongbook-backend wrongbook-frontend
sudo systemctl start wrongbook-backend wrongbook-frontend
```
