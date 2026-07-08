# UniMatch Backend

FastAPI 后端服务。

## 本地开发

```bash
cd services/backend
cp .env.example .env
# 编辑 .env 填入数据库、邮箱、AI API Key 等

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 启动数据库、Redis、MinIO
docker compose -f ../../infra/docker-compose.yml up -d

# 创建表并初始化问卷
python -c "import asyncio; from unimatch.database import init_db; from unimatch.main import seed_questionnaires; asyncio.run(init_db()); asyncio.run(seed_questionnaires())"

# 启动服务
uvicorn unimatch.main:app --reload --host 0.0.0.0 --port 8000
```

## 邮件配置

- 开发环境默认 `MAIL_PROVIDER=mock`，验证码会打印在控制台。
- 使用 126 邮箱：设置 `MAIL_PROVIDER=smtp`，`SMTP_HOST=smtp.126.com`，`SMTP_PORT=465`，`SMTP_USER=yourname@126.com`，`SMTP_PASSWORD=客户端授权码`。
- 使用上海科技大学邮箱：`SMTP_HOST=smtp.shanghaitech.edu.cn`，`SMTP_PORT=465`，`SMTP_PASSWORD=客户端专用密码`。注意校外需连接校园 VPN。

## 短信配置

- 开发环境默认 `SMS_PROVIDER=mock`，验证码打印在控制台。
- 生产可切换为 `twilio`/`tencent`/`aliyun`。

## AI 配置

支持 provider：`deepseek`、`kimi`、`lmstudio`、`opencode`、`mimo`。在 `.env` 中设置对应 API Key。
LMStudio 使用本地 `lms` 启动的模型时，设置 `LMSTUDIO_BASE_URL=http://localhost:1234/v1`。

## 测试

```bash
pytest
```
