# SKDMatch 部署指南 — 三路径让多人访问

> 队伍 c-4 · Philia · SKDMatch 科爱捏校内互助交流平台

---

## 0. 网络拓扑真相（先读，避免踩坑）

| 事实 | 说明 |
|------|------|
| `foundit.geekpie.club` → **10.15.28.8** | 校园网**内网** IP，server: nginx。本质 = 一台**常驻校园网**的机器 + 内网 DNS A 记录。不是"校外笔记本临时开服务"。 |
| atrust 是**出向** VPN | 让你的 Windows 能**访问**校园网资源，但**不让校园网别人入站访问你的笔记本**（VPN 客户端在 NAT 后，校园网防火墙不放行入站）。所以"用 atrust 把校外笔记本变成校园网服务器供他人访问"**不成立**。 |
| WSL2 网络 | 与 Windows 宿主机隔一层 NAT；WSL 看不到 atrust 的 tun 接口、没有 10.x 校园网 IP；WSL 出外网唯一通道是 http_proxy（代理），**直连公网不通**。 |
| cloudflared 隧道 | 用 QUIC/h2 **直连** Cloudflare 边缘，**不走 HTTP 代理**。所以 **WSL 内 cloudflared 连不上边缘 → 隧道在 WSL 跑不通**。隧道必须在**能直连公网**的机器跑 = Windows 宿主机 或 云服务器。 |

**结论**：
- 想让别人（含校外评委）访问 → 用**路径 A**（公网隧道，在 Windows 或云服跑 cloudflared）。
- 想复刻 foundit 的校园网域名 → 用**路径 B**（需要一台常驻校园网的机器 + 能加 DNS 记录）。
- 路演现场评委与你在同一 WiFi → 用**局域网演示**（最稳，零配置，见末节）。

---

## 路径 A：公网隧道（推荐 · 无服务器也能让任何人访问）

### 原理
Cloudflare Tunnel（cloudflared）在你本机开一条**出站**加密隧道到 Cloudflare 边缘，边缘给你一个 `https://xxx.trycloudflare.com` 临时域名，全球任何人访问该域名 → CF 边缘 → 隧道 → 你的本地服务。**不需要公网 IP、不需要开端口、不需要校园网机器**。

### 前提
- 你的服务（backend + frontend）已在某台机器上跑着，绑定 `0.0.0.0`。
- **跑 cloudflared 的那台机器能直连公网**（不被代理/防火墙阻断 QUIC/h2 到 CF 边缘）。

### 场景 A1：服务在 WSL，人在校外（最常见）

WSL 能跑服务但 cloudflared 连不上 CF → **在 Windows 宿主机跑 cloudflared**，指向 WSL 的端口（Windows 能经 localhost 访问 WSL 端口）。

**步骤**：

1. **WSL 里起服务**（绑定 0.0.0.0）：
   ```bash
   cd /path/to/STUMatch
   bash deploy/run-demo.sh
   # 或手动：
   # 后端
   cd services/backend && source .venv/bin/activate
   STORAGE_PROVIDER=local CORS_ORIGINS='*' uvicorn unimatch.main:app --host 0.0.0.0 --port 8001
   # 前端（另一个终端）
   cd apps/web && VITE_API_BASE_URL=http://localhost:8001 npm run dev -- --host 0.0.0.0
   ```

2. **Windows 下载 cloudflared**：
   - 去 https://github.com/cloudflare/cloudflared/releases/latest 下载 `cloudflared-windows-amd64.exe`，重命名为 `cloudflared.exe` 放桌面或 PATH 里。

3. **Windows PowerShell 开后端隧道**：
   ```powershell
   .\cloudflared.exe tunnel --url http://localhost:8001
   ```
   终端会打印类似：
   ```
   Your quick Tunnel has been created! Visit it at:
   https://random-words-1234.trycloudflare.com
   ```
   记下这个 URL，称为 **BACKEND_URL**。

4. **WSL 里用 BACKEND_URL 重新 build 前端**（让前端知道 API 在哪）：
   ```bash
   cd apps/web
   VITE_API_BASE_URL="https://random-words-1234.trycloudflare.com" npm run build
   npx vite preview --host 0.0.0.0 --port 4173
   ```

5. **Windows PowerShell 开前端隧道**：
   ```powershell
   .\cloudflared.exe tunnel --url http://localhost:4173
   ```
   得到 **FRONT_URL**（另一个 `https://xxx.trycloudflare.com`）。

6. **把 FRONT_URL 发给任何人**，他们打开即可体验完整应用。

> **注意**：quick tunnel 域名每次重启 cloudflared 都会变。演示期间保持两个 PowerShell 窗口不关即可。要固定域名需用 named tunnel + 自有 Cloudflare 域名（见进阶）。

### 场景 A2：有一台能直连公网的 Linux 机

同机跑服务 + cloudflared，步骤同上但全在一台机器：
```bash
# 起服务
bash deploy/run-demo.sh
# 开隧道（两个终端或 screen/tmux）
cloudflared tunnel --url http://localhost:8001   # → BACKEND_URL
# 用 BACKEND_URL 重 build 前端
cd apps/web && VITE_API_BASE_URL="$BACKEND_URL" npm run build
npx vite preview --host 0.0.0.0 --port 4173 &
cloudflared tunnel --url http://localhost:4173   # → FRONT_URL（发人）
```

### 进阶：固定域名（named tunnel）

```bash
# 登录 CF（需自有域名托管在 Cloudflare）
cloudflared tunnel login
cloudflared tunnel create skdmatch
# 配置 DNS
cloudflared tunnel route dns skdmatch skdmatch.yourdomain.com
# 配置文件 ~/.cloudflared/config.yml
cat > ~/.cloudflared/config.yml <<EOF
tunnel: skdmatch
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json
ingress:
  - hostname: skdmatch.yourdomain.com
    service: http://localhost:4173
  - hostname: api-skdmatch.yourdomain.com
    service: http://localhost:8001
  - service: http_status:404
EOF
cloudflared tunnel run skdmatch
```
然后前端 build 时 `VITE_API_BASE_URL=https://api-skdmatch.yourdomain.com`。

---

## 路径 B：校园网内网部署（复刻 foundit）

### 前提（缺一不可）
1. 你有一台**长期在线、在校园网有固定/可达 IP** 的机器（实验室服务器 / 学校云主机 / geekpie 等社团机器）。
2. 你能在某个**你能控制的子域**加 A 记录（如 `skdmatch.geekpie.club` → 该机内网 IP；geekpie.club 是社团域，需联系 geekpie 管理员加记录；或用学校提供的内网域名 / 直接 IP 访问）。

> **atrust 校外连入 ≠ 该机在校内**。若你只有校外笔记本 + atrust，此路径**不可行**，请用路径 A。

### 步骤

1. **在该机上部署**（假设 Ubuntu/Debian，有 sudo）：
   ```bash
   # 装依赖
   sudo apt update && sudo apt install -y nginx python3 python3-venv nodejs npm postgresql postgresql-contrib redis-server

   # 克隆仓库
   git clone https://github.com/tzhazuma/STUMatch.git && cd STUMatch

   # 后端
   cd services/backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   # 配置 .env（SECRET_KEY、DATABASE_URL 指向本机 pg 等）
   cp .env.example .env  # 或手动创建
   # 编辑 .env: DATABASE_URL=postgresql+asyncpg://unimatch:unimatch@localhost:5432/unimatch
   #             REDIS_URL=redis://localhost:6379/0
   #             STORAGE_PROVIDER=local
   #             CORS_ORIGINS=*   # 或精确 origin
   #             SECRET_KEY=<随机串>
   # 初始化数据库
   # (确保 pg 已创建 unimatch 库 + pgvector 扩展)
   uvicorn unimatch.main:app --host 127.0.0.1 --port 8001 &

   # 前端（同源部署，baseURL 留空）
   cd ../../apps/web
   npm install
   VITE_API_BASE_URL="" npm run build
   sudo cp -r dist/* /var/www/unimatch/

   # nginx
   sudo cp ../../deploy/nginx.conf /etc/nginx/sites-available/unimatch
   sudo ln -s /etc/nginx/sites-available/unimatch /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```

2. **防火墙放行**：
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp  # 如果用 https
   ```

3. **加 DNS A 记录**：
   - 联系 geekpie 管理员：`skdmatch.geekpie.club  A  10.x.x.x`（该机内网 IP）。
   - 或用学校内网 DNS 管理面板加记录。
   - 或直接用 `http://10.x.x.x` 访问（无域名，但校园网内可达）。

4. **校园网内任何人**访问 `http://skdmatch.geekpie.club` 即可体验。

---

## 路径 C：公网云服务器

### 步骤

1. **买/用云主机**（阿里云/腾讯云/华为云/AWS 等，有公网 IP）。

2. **装环境 + 部署**（同路径 B 步骤 1，但 `server_name` 改为你的域名或 `_`）。

3. **域名解析**（可选）：在域名 DNS 加 A 记录指向公网 IP。无域名则直接 `http://公网IP` 访问。

4. **HTTPS**（推荐）：
   - 简单：套 Cloudflare（域名 NS 指向 CF，开橙色云朵代理，自动 HTTPS）。
   - 或：`sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx`（Let's Encrypt 自动证书）。

5. **systemd 保活后端**（示例）：
   ```ini
   # /etc/systemd/system/unimatch-backend.service
   [Unit]
   Description=SKDMatch Backend
   After=network.target postgresql.service redis.service

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/STUMatch/services/backend
   Environment="PATH=/opt/STUMatch/services/backend/.venv/bin:/usr/bin"
   EnvironmentFile=/opt/STUMatch/services/backend/.env
   ExecStart=/opt/STUMatch/services/backend/.venv/bin/uvicorn unimatch.main:app --host 127.0.0.1 --port 8001 --workers 2
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload && sudo systemctl enable --now unimatch-backend
   ```

---

## 局域网演示（路演现场最稳 · 零配置）

若路演现场评委与你的笔记本在**同一 WiFi / 同一局域网**：

```bash
bash deploy/run-demo.sh
```

脚本会：
1. 起数据层（pg + redis，用 /tmp 用户态编译或 docker）。
2. 起 backend 绑 `0.0.0.0:8001`，CORS=`*`。
3. 探测本机 LAN IP（如 `192.168.1.100`）。
4. build 前端（`VITE_API_BASE_URL=http://192.168.1.100:8001`）。
5. 起 `vite preview` 绑 `0.0.0.0:4173`。
6. 打印：
   ```
   Local:   http://localhost:4173
   LAN:     http://192.168.1.100:4173
   ```

**同局域网的任何设备**（评委手机连同一 WiFi、其他笔记本）打开 LAN URL 即可多人体验，**不需要隧道、不需要公网、不需要校园网机器**。

> 路演建议：提前到场连 WiFi，跑 `run-demo.sh`，把 LAN URL 生成二维码贴海报/白板，评委扫码即体验。

---

## 代码改造说明（已完成）

| 文件 | 改动 | 效果 |
|------|------|------|
| `apps/web/src/api/client.ts` | baseURL 支持空/相对（同源 nginx）与绝对（隧道/LAN） | 同源部署零配置；不同源 build 时注入 |
| `apps/web/src/hooks/useWebSocket.ts` | WS 地址：空→跟随页面 origin；绝对→http→ws 替换 | 隧道 https 自动得 wss |
| `services/backend/unimatch/config.py` | 新增 `CORS_ORIGINS: str = "*"` | 环境变量可配，演示期 `*` 最省事 |
| `services/backend/unimatch/main.py` | CORS 参数化，`*` 时 `allow_credentials=False`（规范） | 非 localhost origin 不再被拦 |

---

## 常见问题

**Q: WSL 里跑 cloudflared 报连接失败？**
A: 预期行为。WSL 无直连公网，cloudflared 不走 HTTP 代理。请在 Windows 宿主机跑 cloudflared，指向 `http://localhost:端口`（Windows 能经 localhost 转发访问 WSL 端口）。

**Q: atrust 连着，校园网别人能访问我的笔记本吗？**
A: 不能。atrust 是出向 VPN，不提供入站。校园网别人访问你需要路径 B（常驻校园网机器）或路径 A（公网隧道）。

**Q: quick tunnel 域名每次变，演示时怎么保证不断？**
A: 演示期间保持两个 cloudflared 进程不关。若需固定域名，用 named tunnel + 自有 CF 域（见路径 A 进阶）。

**Q: 前端刷新深链 404？**
A: 同源 nginx 部署已配 `try_files ... /index.html`（SPA fallback）。`vite preview` 也自带 fallback。若用其他静态服务器（如 `python -m http.server`），需自行配 fallback 或改用 HashRouter（不推荐改路由）。

**Q: CORS 报错 `credentials flag + wildcard origin`？**
A: 代码已处理：`CORS_ORIGINS=*` 时自动 `allow_credentials=False`。若前端某请求需带 cookie（当前不需要），则把 `CORS_ORIGINS` 改为精确 origin 列表。

---

## 实际部署记录（2026-07-30）

### 路径 B：校园网内网 ✅

- **服务器**：`tangzh@10.19.138.148`（Ubuntu 24.04, 112 核, 512GB RAM）
- **访问地址**：`http://10.19.138.148:8888`（nginx 同源反代）或 `http://10.19.138.148:4173`（vite preview 直连）
- **后端 API**：`http://10.19.138.148:8001/docs`
- **部署方式**：apt 装 PostgreSQL 16 + pgvector 0.6 + Redis 7 + nginx；Python venv + uvicorn；前端 `VITE_API_BASE_URL=""` build（同源）+ nginx 8888 端口反代
- **校园网内任何设备**（含 atrust 连入的校外设备）打开上述地址即可体验

### 路径 A：公网隧道 ✅

- **隧道工具**：cloudflared quick tunnel（运行在校园网服务器上，该服务器有公网出口）
- **公网访问地址**：`https://radical-scholars-plots-beyond.trycloudflare.com`
- **原理**：cloudflared 在 10.19.138.148 上开出站隧道到 Cloudflare 边缘 → 边缘分配临时域名 → 全球任何人访问该域名 → CF 边缘 → 隧道 → nginx 8888 → 前端静态 + API 反代
- **注意**：quick tunnel 域名在 cloudflared 进程重启后会变；演示期间保持进程在线即可
- **校外评委/任何人**无需校园网、无需 atrust，直接打开上述 HTTPS 链接即可体验完整应用

### 部署脚本（可复现）

远程服务器上保留的脚本：
- `~/rd.sh` — 首次部署（apt + pg + redis + venv + pip + backend + frontend build）
- `~/rncf.sh` — nginx 配置 + cloudflared 隧道
- `~/remote_fix_nginx_cf.sh` — nginx 修复 + cloudflared 启动

WSL 侧 SSH 桥接方式（因 WSL 无法直连 10.x 校园网 IP）：
```bash
# 通过 Windows 宿主机 SSH 转发
powershell.exe -Command "
  \$env:SSH_ASKPASS='C:\Users\tzh03\askpass.cmd';
  \$env:SSH_ASKPASS_REQUIRE='force';
  \$env:DISPLAY='dummy';
  ssh -o StrictHostKeyChecking=no tangzh@10.19.138.148 '<command>'
"
```
