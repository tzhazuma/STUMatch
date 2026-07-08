# UniMatch 校园同学匹配交友平台

> Web + 后端 + 移动端（Expo）一体化校园匹配平台。先完成基础功能，AI 训练/微调、学校统一身份认证后续对接。

---

## 快速启动（本地开发）

```bash
# 1. 复制环境变量
cp .env.example .env
# 编辑 .env 填入你的邮箱、AI API Key 等

# 2. 启动数据库、缓存、对象存储
docker compose -f infra/docker-compose.yml up -d

# 3. 安装后端依赖并运行
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/backend/requirements.txt
cd services/backend
alembic upgrade head
uvicorn unimatch.main:app --reload --port 8000

# 4. 启动前端
cd apps/web
npm install
npm run dev

# 5. 启动移动端（见 apps/mobile/README.md）
```

---

## 目录结构

```
.
├── apps
│   ├── web/                 # React + Vite + TypeScript
│   └── mobile/              # Expo (React Native)
├── services
│   ├── backend/               # FastAPI + SQLAlchemy + Alembic
│   └── ai/                    # AI 网关占位与本地模型配置
├── infra
│   └── docker-compose.yml   # PostgreSQL + Redis + MinIO
├── docs
│   └── API_CONTRACT.md        # 前后端/移动端统一 API 契约
├── .env.example
└── README.md
```

---

## 技术栈

- 后端：Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + Celery + Redis + PostgreSQL(pgvector) + MinIO
- 前端：React 18 + Vite + TypeScript + Tailwind CSS + TanStack Query + React Router + Zustand
- 移动端：Expo + React Native + TypeScript
- AI：OpenAI SDK 兼容网关，支持 DeepSeek / Kimi / LMStudio / OpenCode / MIMO（后两者待确认）

---

## 环境变量

见 `.env.example`。关键变量：

- `DATABASE_URL`, `REDIS_URL`
- `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `MAIL_PROVIDER`：`netease_126` 或 `shanghaitech`
- `SMS_PROVIDER`：`mock` / `twilio` / `aliyun` / `tencent`
- AI：`DEEPSEEK_API_KEY`, `KIMI_API_KEY`, `LMSTUDIO_BASE_URL`, `OPENCODE_API_KEY`, `MIMO_API_KEY`
- 文件存储：`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`

---

## 许可证与合规

本项目用于校园创新实践，收集的邮箱、手机号、聊天记录等敏感信息需遵守《个人信息保护法》及学校相关规定。身份证号不收集。
