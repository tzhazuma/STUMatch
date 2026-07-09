# UniMatch 项目完整说明文档

> 文档版本：v0.1.0
> 编写目的：记录 UniMatch 校园同学匹配交友平台的产品思路、功能设计、技术架构与实现细节，方便后续在任意设备上继续开发。

---

## 1. 项目概述

### 1.1 背景与目标

UniMatch 是一个面向上海科技大学及类似高校学生的**校内同学匹配交友平台**。初衷是解决校园生活中“找学习伙伴、找兴趣搭子、找恋爱对象”的需求。平台通过问卷初步刻画用户画像，结合 AI 分析聊天记录与用户反馈，持续优化匹配推荐，并提供一个类微信的单聊功能。

与纯恋爱交友平台（如 MatchUS）不同，UniMatch 覆盖三大场景：

- **学术交流**：找同专业、同研究方向、互补技能的科研/学习伙伴。
- **日常生活**：找旅行、游戏、运动、美食等“搭子”。
- **恋爱交友**：基于年龄、兴趣、性格、现居地等维度的恋爱匹配。

### 1.2 产品定位

| 维度 | 定位 |
|------|------|
| 用户 | 高校在校学生 |
| 场景 | 学术、兴趣、恋爱三板块 |
| 核心交互 | 问卷画像 → 智能推荐 → 加好友 → 聊天 |
| 数据边界 | 校内闭环，最小化收集敏感信息；不强制收集身份证 |
| 技术特色 | 云端大模型 + 本地小模型蒸馏；可自迭代的匹配与审核系统 |

---

## 2. 核心功能

### 2.1 注册与认证

- **邮箱验证码注册/登录**：默认使用学校邮箱（`@shanghaitech.edu.cn`）注册，可通过环境变量 `ALLOWED_EMAIL_DOMAINS` 配置多个允许后缀（逗号分隔）。也支持 126/163 等 SMTP 发送验证码，开发环境使用 mock 打印验证码。
- **手机号验证码**：支持 Twilio/阿里云/腾讯云短信，开发环境 mock。
- **学校统一身份认证（预留）**：已实现 CAS 客户端配置占位，待与学校网络信息中心沟通后接入。
- **实名认证**：不强制收集身份证号。优先通过校内统一认证验证学生身份；如未来需要，可接入阿里云/腾讯云/聚合数据实名接口。
- **启动强校验**：后端启动时会检查 `SECRET_KEY` 是否已设置，未设置将直接报错，防止使用默认密钥上线。

### 2.2 个人资料

- 头像、昵称、性别、出生日期、年龄、学历、学校、专业、MBTI、兴趣爱好、现居地、个人介绍。
- 学术交流：研究方向、想要学术交流的方向。
- 恋爱交友：交友目的、想遇见的人、家庭状况。
- 邮箱/学校认证状态、用户授权同意记录。

### 2.3 发现页

- 顶部导航：**发现、好友、个人**。
- 三个板块：学术交流、日常生活、恋爱交友。
- 每个板块支持搜索（昵称、专业、学校、兴趣）和“开启推送”。
- 用户卡片展示板块相关字段；点击进入用户主页。
- 未完善资料或未认证时，点击“加好友”/“开启推送”弹窗提示：“完善交友资料，开启精确匹配”。

### 2.4 匹配推荐

- **第一期**：规则 + `pgvector` 向量相似度。
  - 学术：先专业，再学历，再学校。
  - 日常：先兴趣，再年龄。
  - 恋爱：先年龄差 ≤ 2，再兴趣，再同城。
- 开启推送后，优先展示系统选出的 Top 10 高匹配用户，其余随机排列。
- 用户可对推荐反馈：喜欢 / 不喜欢 / 跳过，用于后续优化。
- **未来**：引入 Faiss/Milvus、LightFM、LLM 聊天分析、DPO/RLHF 自迭代。

### 2.5 问卷系统

- 后端支持 `single_choice`、`multiple_choice`、`text`、`rating`、`tags`、`date` 题型。
- 已内置问卷：
  - `basic`：基础资料（性别、学历、专业、兴趣、MBTI、现居地等）。
  - `academic`：20 题学术交流问卷，覆盖研究经验/能力、研究兴趣、匹配偏好、个人偏好。
  - `daily`：日常生活兴趣。
  - `dating`：恋爱交友资料（交友目的、MBTI、兴趣、个人介绍、理想伴侣、家庭状况）。
- AI 可根据用户画像生成进阶问题，进一步细化匹配。

### 2.6 聊天

- 类微信**单聊**（文字、图片、emoji）。
- Web 端通过 WebSocket 实时收发；移动端通过 REST 兜底。
- 消息发送前本地敏感词过滤；严重违规直接拦截并提示“包含违禁词”。
- 消息已读、未读红泡、好友申请。
- 聊天记录加密存储，默认保留 3–6 个月。

### 2.7 内容审核与安全

- **本地层**：DFA/Trie 敏感词库（中文），覆盖色情、赌博、毒品、诈骗、辱骂等。
- **云端层**：预留 OpenAI Moderation / 阿里云内容安全 / 腾讯云 TMS 接口，可异步复核。
- **举报系统**：用户可举报用户/消息/内容，后台工单处理。
- **审计日志**：记录关键操作与审核结果。

### 2.8 管理后台

- 用户管理、状态封禁。
- 举报工单处理。
- 审核日志查看。
- 问卷管理（未来扩展）。

### 2.9 AI 模块

- **AI 网关**：统一调用 OpenAI SDK 兼容接口，支持：
  - 云端：DeepSeek、Kimi（Moonshot）、OpenCode（待确认）、MIMO（待确认）。
  - 本地：LMStudio（通过 `lms` 运行 Qwen/Gemma 等）。
- **功能**：生成进阶问题、生成匹配解释、聊天内容摘要、辅助审核。
- **自迭代**：收集显式反馈（喜欢/不喜欢/举报）与隐式反馈（聊天时长、回复率），匿名化后构建 SFT/DPO 数据，周期性用 QLoRA 微调本地模型。
- **本期**：仅配置网关，不实际训练。

---

## 3. 技术架构

### 3.1 技术栈

| 层级 | 技术 |
|------|------|
| Web 前端 | React 18 + Vite + TypeScript + Tailwind CSS + TanStack Query + React Router + Zustand |
| 移动端 | Expo + React Native + TypeScript + React Navigation + AsyncStorage |
| 后端 | Python 3.11 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic |
| 数据库 | PostgreSQL 16 + `pgvector` 扩展 |
| 缓存/会话 | Redis 7 |
| 对象存储 | MinIO（S3 兼容）/ 本地文件系统 |
| 异步任务 | Celery + Redis |
| 认证 | JWT + python-jose + bcrypt |
| 聊天 | 自研 WebSocket |
| 向量检索 | `pgvector`（未来可扩展 Faiss/Milvus） |
| AI | OpenAI SDK 兼容网关 + Ollama/LMStudio + QLoRA（未来） |
| 部署 | Docker Compose + Nginx |

### 3.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                              │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  Web App   │  │ Android App  │  │   Admin Web (未来)  │   │
│  │ React+Vite │  │ Expo (RN)    │  │   Refine/AntD     │   │
│  └──────┬─────┘  └──────┬───────┘  └─────────┬──────────┘   │
└─────────┼──────────────┼────────────────────┼──────────────┘
          │              │                    │
          └──────────────┼────────────────────┘
                         │ HTTPS
                ┌────────┴────────┐
                │     Nginx       │
                └────────┬────────┘
                         │
          ┌──────────────────────────────┐
          │      FastAPI 后端服务          │
          │  - 认证 / 实名 / 验证码        │
          │  - 资料 / 发现 / 匹配          │
          │  - 问卷 / 响应                 │
          │  - 好友 / 聊天 WebSocket       │
          │  - 审核 / 举报 / AI 网关        │
          │  - 文件上传                     │
          └──────────────┬───────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
┌──────┴──────┐ ┌────────┴────────┐ ┌──────┴──────┐
│  PostgreSQL │ │      Redis       │ │    MinIO    │
│  + pgvector │ │ 会话/缓存/限流/队列 │ │  图片存储   │
└─────────────┘ └──────────────────┘ └─────────────┘
       │                 │
       │       ┌─────────┴─────────┐
       │       │   Celery Workers  │
       │       │ 发送邮件/短信/审核 │
       │       └───────────────────┘
       │
       │ 未来扩展：AI 服务
       │ ┌──────────────────────────────────┐
       │ │  Ollama / LMStudio / vLLM        │
       │ │  + 云端 LLM API 网关              │
       │ └──────────────────────────────────┘
```

### 3.3 数据流

```
用户注册/登录 → 填写问卷 → 生成/更新画像向量
       ↓
匹配引擎（规则 + pgvector 余弦相似度）→ 推荐 Top-N
       ↓
发起好友申请 → 通过聊天互动 → 产生行为数据
       ↓
收集反馈（喜欢/不喜欢/举报/聊天时长）
       ↓
云端大模型/本地小模型分析 → 生成标签、优化问题
       ↓
周期性微调（QLoRA）→ 更新匹配权重/向量/规则
       ↓
下一轮推荐
```

---

## 4. 目录结构

```
unimatch/
├── apps/
│   ├── web/                    # React + Vite + TypeScript
│   │   ├── src/
│   │   │   ├── api/            # axios 客户端 + 接口封装
│   │   │   ├── components/     # UI 组件、Layout、UserCard
│   │   │   ├── hooks/          # useAuth, useApi, useWebSocket
│   │   │   ├── pages/          # Login, Discovery, Profile, Chat, ...
│   │   │   ├── store/          # Zustand auth store
│   │   │   └── types/          # TypeScript 类型
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── tailwind.config.js
│   └── mobile/                 # Expo + React Native
│       ├── src/
│       │   ├── api/
│       │   ├── components/
│       │   ├── navigation/
│       │   ├── screens/
│       │   ├── hooks/
│       │   ├── store/
│       │   └── types/
│       ├── app.json
│       ├── package.json
│       └── scripts/
│           └── install-android-sdk.sh
├── services/
│   ├── backend/                  # FastAPI 后端
│   │   ├── unimatch/
│   │   │   ├── main.py           # 应用入口、问卷种子
│   │   │   ├── config.py         # 环境变量配置
│   │   │   ├── database.py       # 数据库引擎、pgvector
│   │   │   ├── models.py         # SQLAlchemy 模型
│   │   │   ├── schemas.py        # Pydantic 请求/响应模型
│   │   │   ├── security.py       # JWT、密码、当前用户依赖
│   │   │   ├── routers/          # 路由模块
│   │   │   ├── services/         # 业务服务（邮件、短信、审核、AI、匹配）
│   │   │   └── tasks.py          # Celery 任务
│   │   ├── alembic/              # 迁移配置
│   │   ├── tests/                # pytest 测试
│   │   └── requirements.txt
│   └── ai/                       # AI 模块文档与配置占位
│       └── README.md
├── infra/
│   └── docker-compose.yml        # PostgreSQL + Redis + MinIO
├── docs/
│   ├── API_CONTRACT.md           # 前后端/移动端 API 契约
│   └── PROJECT_GUIDE.md          # 本说明文档
├── .github/
│   └── workflows/
│       └── ci.yml                # GitHub Actions CI
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
└── README.md
```

---

## 5. 后端详细说明

### 5.1 主要路由

| 路由 | 说明 |
|------|------|
| `/auth/*` | 注册、登录、验证码、刷新、退出 |
| `/users/*` | 当前用户 CRUD |
| `/profiles/*` | 个人资料、头像上传、用户授权 |
| `/discovery/*` | 三板块发现、搜索、推送开关 |
| `/questionnaires/*` | 问卷列表、详情、答卷、我的答卷 |
| `/matches/*` | 推荐、反馈 |
| `/friends/*` | 好友申请、接受/拒绝、好友列表 |
| `/conversations/*` | 会话列表、消息历史、REST 发送 |
| `/ws/chat` | WebSocket 实时聊天 |
| `/message-board/*` | 留言板 |
| `/reports/*` | 举报 |
| `/admin/*` | 管理后台接口 |
| `/ai/*` | AI 生成问题、匹配解释 |

### 5.2 核心模型

- `User`：基础账号、认证状态、角色。
- `Profile`：用户画像、向量、各板块推送开关。
- `UserConsent`：用户授权记录。
- `Questionnaire` / `QuestionnaireResponse`：问卷定义与答案。
- `MatchFeedback`：推荐反馈。
- `Friendship`：好友申请与关系。
- `Conversation` / `Message`：单聊会话与消息。
- `MessageBoard`：留言板。
- `Report` / `ModerationLog`：举报与审核日志。

### 5.3 匹配服务

- 将用户的资料字段与问卷答案拼接成文本。
- 使用基于哈希的确定性向量作为 MVP 方案（生产环境应替换为 `BGE-M3` 或 `multilingual-e5-large`）。
- 存入 `pgvector` 后，使用余弦距离检索候选。
- 按板块规则打分，返回 Top-N 并附带匹配理由。

### 5.4 AI 网关

```python
# 配置示例
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

- 所有 provider 统一使用 OpenAI SDK 的 `base_url` + `api_key` 方式。
- `OpenCode` 和 `MIMO` 为占位，需确认官方 API 后补充。
- LMStudio 本地模型：启动 `lms` 后设置 `LMSTUDIO_BASE_URL=http://localhost:1234/v1`。

---

## 6. 前端/移动端详细说明

### 6.1 Web 前端

- 登录/注册二合一页面，支持邮箱验证码。
- 发现页：三板块 Tab、搜索、推送开关、用户卡片列表。
- 用户详情：展示板块相关字段、加好友、聊天入口。
- 个人资料：编辑所有字段、上传头像。
- 问卷页：动态渲染题型并提交。
- 好友页：好友申请、接受/拒绝、好友列表。
- 聊天页：WebSocket 实时单聊，REST 兜底。

### 6.2 移动端

- 登录/注册页（与 Web 逻辑一致）。
- 底部导航：发现、好友、个人。
- 发现页、用户详情、个人资料、好友、聊天、问卷页面。
- 头像使用 `expo-image-picker` 从相册选择并上传。
- 聊天使用 REST 接口（WebSocket 可在后续版本接入）。

---

## 7. 环境变量

详见 `.env.example`，核心变量：

```ini
# 数据库与缓存
DATABASE_URL=postgresql+asyncpg://unimatch:unimatch@localhost:5432/unimatch
REDIS_URL=redis://localhost:6379/0

# 邮件（mock / 126 / 上海科技大学）
MAIL_PROVIDER=mock
SMTP_HOST=smtp.126.com
SMTP_PORT=465
SMTP_USER=yourname@126.com
SMTP_PASSWORD=客户端授权码

# 短信（mock / twilio / aliyun / tencent）
SMS_PROVIDER=mock

# AI 提供商
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx
KIMI_API_KEY=sk-xxx
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# 存储
STORAGE_PROVIDER=local
```

---

## 8. 快速开始

### 8.1 启动基础设施

```bash
cd /path/to/unimatch
docker compose -f infra/docker-compose.yml up -d
```

### 8.2 启动后端

```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn unimatch.main:app --reload --host 0.0.0.0 --port 8000
```

### 8.3 启动 Web 前端

```bash
cd apps/web
npm install
npm run dev
```

### 8.4 启动移动端

```bash
cd apps/mobile
npm install
npx expo start
# 扫描 QR 码用 Expo Go 预览，或按 a 启动 Android 模拟器
```

### 8.5 构建 APK

```bash
bash apps/mobile/scripts/install-android-sdk.sh
```

---

## 9. 安全与合规

- **敏感信息最小化**：不强制收集身份证号；手机号/邮箱可加密存储；聊天记录加密。
- **用户授权**：隐私政策、实名授权、聊天记录分析授权均需单独同意并可撤销。
- **数据保留**：聊天记录 3–6 个月；账号注销后 30 天内删除或匿名化。
- **内容审核**：本地敏感词 + 云端 API 复核；人工后台兜底。
- **访问控制**：JWT 鉴权、RBAC 后台、审计日志。
- **部署建议**：优先校内服务器或国内云，避免数据出境合规风险。

---

## 10. 未来计划

1. **接入学校统一身份认证**：与 ITC 沟通 CAS/OAuth 接入。
2. **真实向量模型**：接入 `BGE-M3` 或 `multilingual-e5-large` 生成语义 embedding。
3. **高级推荐算法**：引入 Faiss/Milvus + LightFM + TensorFlow Recommenders。
4. **AI 自迭代**：收集反馈数据，用 QLoRA 微调本地 Qwen/Gemma 模型。
5. **群聊与活动**：在单聊基础上增加学习小组、兴趣社团群。
6. **推送通知**：浏览器 Push、FCM、极光推送。
7. **iOS 支持**：在 Expo 基础上增加 iOS 构建。
8. **管理后台完善**：可视化问卷编辑、举报工单、内容审核。

---

## 11. 贡献与联系方式

- 仓库地址：https://github.com/tzhazuma/STUMatch
- 提交规范：见 `CONTRIBUTING.md`。
- 分支命名：`feature/xxx`、`fix/xxx`、`docs/xxx`。
- 提交前运行 `pytest`（后端）和 `npm run build`（Web）。

---

> 本文档会随项目迭代持续更新。如需补充或修改，请直接在 `docs/PROJECT_GUIDE.md` 中编辑并提交 PR。
