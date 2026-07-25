#!/usr/bin/env python3
"""Record a LIVE demo of the running SKDMatch web app with Playwright.

PREREQUISITES (run these FIRST in a terminal where the app is up):
  1. infra:   docker-compose -f infra/docker-compose.yml up -d
  2. backend: cd services/backend && source .venv/bin/activate && uvicorn unimatch.main:app --host 0.0.0.0 --port 8001
  3. web:     cd apps/web && npm run dev -- --host 0.0.0.0
  4. seed:    (in backend venv) python /tmp/setup_demo_data.py   # prints CONVERSATION_ID=...
  5. pip install playwright httpx  (chromium at /usr/bin/chromium-browser on this box)

Then:  python3 scripts/finals/record_live_demo.py
Output: a webm under /tmp/record_vid  (path printed at the end as LIVE_WEBM=...)
Override via env: BASE_WEB, BASE_API, EMAIL, PASSWORD, CONVERSATION_ID, OUT_DIR.
"""
import asyncio, json, os, glob
import httpx
from playwright.async_api import async_playwright

BASE_API = os.environ.get("BASE_API", "http://localhost:8001")
BASE_WEB = os.environ.get("BASE_WEB", "http://localhost:5173")
EMAIL = os.environ.get("EMAIL", "demo-main@shanghaitech.edu.cn")
PASSWORD = os.environ.get("PASSWORD", "password123")
def _read_conv():
    try:
        v = open("/tmp/conv_id").read().strip()
        if v:
            return v
    except Exception:
        pass
    return os.environ.get("CONVERSATION_ID", "8d1c1e67-5f08-480c-8c69-6757c19836e7")


CONV = _read_conv()
OUT_DIR = os.environ.get("OUT_DIR", "/tmp/record_vid")
CHROME = os.environ.get("CHROME", "/usr/bin/chromium-browser")


async def login():
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(f"{BASE_API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["data"]


async def safe(step, coro_fn):
    try:
        await coro_fn()
    except Exception as e:  # never abort the recording on a flaky selector
        print(f"[skip] {step}: {e}")


async def scroll(page, times=4, dy=300, delay=500):
    for _ in range(times):
        await page.mouse.wheel(0, dy)
        await page.wait_for_timeout(delay)


async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    auth = await login()
    storage = {
        "state": {
            "access_token": auth["access_token"],
            "refresh_token": auth["refresh_token"],
            "token_type": auth["token_type"],
            "expires_at": int(asyncio.get_event_loop().time()) * 1000 + auth["expires_in"] * 1000,
            "user": auth["user"],
            "isAuthenticated": True,
        },
        "version": 0,
    }
    init_script = f"localStorage.setItem('unimatch-auth', {json.dumps(json.dumps(storage))});"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=CHROME,
                                          args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=OUT_DIR,
            record_video_size={"width": 1280, "height": 720},
        )
        await context.add_init_script(init_script)
        page = await context.new_page()

        # 1 landing
        await page.goto(f"{BASE_WEB}/", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        await safe("landing-scroll", lambda: scroll(page, 3, 250, 600))
        await page.wait_for_timeout(800)

        # 2 login + register tab + typing
        await page.goto(f"{BASE_WEB}/login", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        await safe("click-register", lambda: page.get_by_text("注册", exact=True).first.click())
        await page.wait_for_timeout(2500)
        await safe("click-login", lambda: page.get_by_text("登录", exact=True).first.click())
        await page.wait_for_timeout(1200)
        await safe("type-email", lambda: page.get_by_placeholder("yourname@shanghaitech.edu.cn").fill("demo@shanghaitech.edu.cn"))
        await page.wait_for_timeout(1200)

        # 3 discovery academic + tabs
        await page.goto(f"{BASE_WEB}/discovery/academic", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        await safe("disc-scroll", lambda: scroll(page, 3, 300, 600))
        await safe("tab-daily", lambda: page.get_by_text("日常生活", exact=True).first.click())
        await page.wait_for_timeout(2200)
        await safe("tab-dating", lambda: page.get_by_text("恋爱交友", exact=True).first.click())
        await page.wait_for_timeout(2200)

        # 4 user detail (click first card)
        await page.goto(f"{BASE_WEB}/discovery/academic", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1200)
        await safe("open-detail", lambda: page.locator("text=加好友").first.click(timeout=4000))
        await page.wait_for_timeout(2500)

        # 5 questionnaire
        await page.goto(f"{BASE_WEB}/questionnaire/basic", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        await safe("q-scroll", lambda: scroll(page, 3, 300, 600))
        await page.wait_for_timeout(800)

        # 6 profile
        await page.goto(f"{BASE_WEB}/profile", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        await safe("prof-scroll", lambda: scroll(page, 4, 350, 600))

        # 7 friends
        await page.goto(f"{BASE_WEB}/friends", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        # 8 chat + send a message
        await page.goto(f"{BASE_WEB}/chat/{CONV}", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        async def send_msg():
            box = page.get_by_placeholder("输入消息...")
            await box.fill("你好，决赛演示：实时聊天可用！")
            await page.wait_for_timeout(800)
            await box.press("Enter")
        await safe("chat-send", send_msg)
        await page.wait_for_timeout(2500)

        video_path = await page.video.path()
        await context.close()
        await browser.close()

    webms = sorted(glob.glob(os.path.join(OUT_DIR, "*.webm")), key=os.path.getmtime)
    final = webms[-1] if webms else video_path
    print("LIVE_WEBM=" + final)


asyncio.run(main())
