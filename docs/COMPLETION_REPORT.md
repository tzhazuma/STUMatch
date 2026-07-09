# UniMatch 完成状态报告

> 报告日期：2026-07-10  
> 仓库：https://github.com/tzhazuma/STUMatch  
> 分支：`main`（最新提交 `5de3a8b`）

---

## 1. 本次处理内容

本报告记录从合作同学 `STUMatch1.zip` 合并代码、推送到 GitHub、修复 GitHub Actions 并验证 Release 的全过程。

### 1.1 从 GitHub 拉取最新代码

```bash
git pull origin main
```

拉取后发现合作同学已将 `STUMatch1.zip` 上传到仓库，因此直接获取了该压缩包。

### 1.2 解压并覆盖当前代码

```bash
unzip -o STUMatch1.zip -d /tmp/stumatch_extract
rsync -av --exclude='.git' --exclude='STUMatch1.zip' /tmp/stumatch_extract/STUMatch/ ./
```

解压后首先发现所有文本文件为 Windows CRLF 换行，导致 `git diff` 显示全部 119 个文件改动。已统一转换为 LF：

```bash
perl -pi -e 's/\r$//' <text files>
```

转换后实际代码改动仅涉及 11 个文件，便于审阅。

### 1.3 合作同学本次引入的关键改动

| 文件 | 改动说明 |
|------|----------|
| `services/backend/unimatch/config.py` | `SECRET_KEY` 默认改为空字符串，新增 `ALLOWED_EMAIL_DOMAINS`（默认 `@shanghaitech.edu.cn`） |
| `services/backend/unimatch/main.py` | 启动时强制校验 `SECRET_KEY`；CORS 限制为本地前端端口 |
| `services/backend/unimatch/models.py` | 移除 PostgreSQL 不适用的 `sqlite_autoincrement` 参数 |
| `services/backend/unimatch/routers/auth.py` | 注册/发送验证码时校验学校邮箱后缀；`logout` 将当前 token 加入 Redis 黑名单 |
| `services/backend/unimatch/routers/chat.py` | 敏感词检测改为线程异步执行，避免阻塞事件循环 |
| `services/backend/unimatch/routers/message_board.py` | 同上，留言板敏感词异步检测 |
| `services/backend/unimatch/routers/friends.py` | 好友申请列表返回 `{ items, total }` 结构 |
| `apps/web/src/pages/Discovery.tsx` | 板块切换使用 `useNavigate`，避免整页刷新 |
| `apps/web/src/pages/Login.tsx` | 验证码发送增加 60 秒倒计时 |

### 1.4 我为合并与上线所做的修复

1. **测试环境适配**  
   `services/backend/tests/conftest.py` 新增：
   ```python
   os.environ["ALLOWED_EMAIL_DOMAINS"] = "example.com"
   ```
   否则测试用 `@example.com` 会被默认的学校邮箱白名单拒绝。

2. **CI 环境变量**  
   `.github/workflows/ci.yml` 的 `backend-tests` job 增加：
   ```yaml
   env:
     SECRET_KEY: test-secret-key-change-in-production
     ALLOWED_EMAIL_DOMAINS: example.com
     MAIL_PROVIDER: mock
     STORAGE_PROVIDER: local
     AI_PROVIDER: deepseek
     DATABASE_URL: postgresql+asyncpg://unimatch:unimatch@localhost:5432/unimatch_test
     REDIS_URL: redis://localhost:6379/15
   ```

3. **环境变量模板更新**  
   `.env.example` 和 `services/backend/.env.example` 均新增 `ALLOWED_EMAIL_DOMAINS=shanghaitech.edu.cn`。

4. **文档同步**  
   - `README.md`：补充 `ALLOWED_EMAIL_DOMAINS`、强调 `SECRET_KEY` 必须设置。
   - `docs/PROJECT_GUIDE.md`：注册认证章节说明邮箱白名单与启动强校验。
   - `docs/API_CONTRACT.md`：说明验证码邮箱后缀限制、`logout` 需携带 token、好友申请列表返回结构。

5. **清理仓库**  
   删除二进制 `STUMatch1.zip` 并在 `.gitignore` 中加入 `*.zip`，避免后续重复提交压缩包。

---

## 2. GitHub Actions 验证结果

推送后触发的两个工作流均已成功：

| 工作流 | 状态 | 耗时 | 关键检查点 |
|--------|------|------|------------|
| `CI` | ✅ success | 1m 9s | 后端 15 项测试通过、Web 构建成功、移动端 TypeScript 检查通过 |
| `Build Android APK and Release` | ✅ success | 约 14m | Expo prebuild、Gradle 构建 APK、Web 打包、Release 发布 |

> 注：GitHub 已提示 `actions/checkout@v4` 与 `actions/setup-node@v4` 基于 Node.js 20 的警告（Actions 强制在 Node 24 上运行），不影响构建结果，可后续升级 action 版本。

---

## 3. GitHub Release 资产

Release 标签：`v0.1.0`

| 资产 | 大小 | 说明 |
|------|------|------|
| `unimatch-release.apk` | ~65 MB | Android 安装包（Expo + React Native release） |
| `unimatch-web-dist.zip` | ~94 KB | Web 前端生产构建包（Vite 输出） |

下载地址：https://github.com/tzhazuma/STUMatch/releases/tag/v0.1.0

---

## 4. 本地验证

在推送前已在本机验证：

- `apps/web`：`npm run build` ✅
- `apps/mobile`：`npx tsc --noEmit` ✅
- `services/backend`：`pytest --collect-only` 成功收集 15 项测试 ✅

完整集成测试需要 Docker Compose 启动 PostgreSQL + Redis。运行方式：

```bash
cd /path/to/STUMatch

docker compose -f infra/docker-compose.yml up -d

cd services/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

---

## 5. 重要配置提醒

部署或继续开发前，请务必在 `.env` 中设置：

```bash
# 至少 32 位随机字符串，未设置后端将拒绝启动
SECRET_KEY=change-this-to-a-random-string-at-least-32-characters-long

# 允许注册的邮箱后缀，可多个逗号分隔
ALLOWED_EMAIL_DOMAINS=shanghaitech.edu.cn
```

生产环境还应配置：

- 真实 SMTP / 短信服务商（`MAIL_PROVIDER` / `SMS_PROVIDER`）
- 托管 PostgreSQL + Redis
- MinIO / S3 对象存储
- 各 AI provider 的 API Key
- HTTPS 反向代理（Nginx / Traefik）

---

## 6. 下一步建议

1. 在学校网络信息中心申请 CAS / OAuth 应用接入，实现校内统一认证。
2. 接入阿里云 / 腾讯云内容安全作为第二道审核（`MODERATION_PROVIDER`）。
3. 收集匹配反馈数据，为本地模型 QLoRA 微调做准备。
4. 完成管理后台（Refine / React Admin）的完整页面。
5. 将 GitHub Actions 中的 `actions/checkout` 与 `actions/setup-node` 升级至 Node 24 原生版本，消除警告。

---

## 7. 相关文档

- `README.md`：项目简介、快速开始、环境变量
- `docs/PROJECT_GUIDE.md`：产品思路、架构、数据模型
- `docs/API_CONTRACT.md`：前后端/移动端 API 契约
- `CONTRIBUTING.md`：贡献规范
- `apps/mobile/BUILD_REPORT.md`：APK 构建环境与排错记录
