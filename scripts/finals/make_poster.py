# -*- coding: utf-8 -*-
"""SKDMatch finals poster v2 — exhibition key-visual, de-AI-ified.

Usage:
  python3 make_poster_v2.py assets   # render PIL brand assets to /tmp/poster_assets
  python3 make_poster_v2.py build    # assemble 60x90cm PDF (needs assets)
  python3 make_poster_v2.py          # both
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = "/mnt/c/Users/tzh03/Downloads/STUMatch2/STUMatch"
ASSETS = os.path.join(ROOT, "finals", "finals_assets")
if not os.path.isdir(ASSETS):
    ASSETS = os.path.join(ROOT, "finals_assets")
SHOTS = os.path.join(ROOT, "screenshots")
OUT_PDF = os.path.join(ROOT, "finals", "c-4_SKDMatch_海报.pdf")
PA = "/tmp/poster_assets"
os.makedirs(PA, exist_ok=True)

LX = "/home/linuxbrew/.linuxbrew/Cellar/texlive/20260301/share/texmf-dist/fonts/truetype/public/lxgw-fonts"
SERIF_TTF = LX + "/LXGWNeoZhiSong.ttf"
SANS_TTF = LX + "/LXGWNeoXiHei.ttf"
MONO_TTF = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB_TTF = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

# palette (RGB)
INK = (16, 16, 21); PAPER = (246, 244, 238); PURPLE = (124, 58, 237); ORANGE = (247, 115, 22)
PURPLE_LT = (237, 233, 254); ORANGE_LT = (255, 237, 213); LINE = (217, 213, 201)
WHITE = (255, 255, 255); INK2 = (40, 40, 48); GREY = (120, 120, 132)
PURPLE_D = (91, 33, 182); ORANGE_D = (234, 88, 12)


def F(path, size):
    return ImageFont.truetype(path, size)


def rgba(c, a):
    return (c[0], c[1], c[2], a)


def glow_dot(layer, cx, cy, r, color, alpha):
    """radial glow: draw filled circle on layer then it'll be blurred by caller."""
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba(color, alpha))


# ---------------------------------------------------------------- hero network
def make_hero():
    W, H = 1500, 980
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rnd = random.Random(11)
    nodes = []
    for _ in range(42):
        x = int(W * (0.34 + 0.62 * (rnd.random() ** 1.7)))
        y = int(H * (0.08 + 0.84 * rnd.random()))
        r = rnd.choice([3, 4, 4, 5, 6, 7, 8, 10])
        col = rnd.choices([WHITE, PURPLE, ORANGE], weights=[2, 4, 3])[0]
        nodes.append((x, y, r, col))
    d = ImageDraw.Draw(base)
    cands = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            x1, y1, r1, _ = nodes[i]; x2, y2, r2, _ = nodes[j]
            dist = math.hypot(x1 - x2, y1 - y2)
            if dist < 210:
                a = int(max(0, 64 - dist * 0.26))
                col = PURPLE if (i + j) % 3 else WHITE
                d.line([(x1, y1), (x2, y2)], fill=rgba(col, a), width=1)
            if 120 < dist < 300:
                cands.append((dist, i, j))
    rnd.shuffle(cands)
    hi = [(i, j) for _, i, j in cands[:3]]
    for i, j in hi:
        x1, y1, r1, _ = nodes[i]; x2, y2, r2, _ = nodes[j]
        d.line([(x1, y1), (x2, y2)], fill=rgba(ORANGE, 165), width=3)
        glow_dot(glow, x1, y1, 24, ORANGE, 130); glow_dot(glow, x2, y2, 24, ORANGE, 130)
    for x, y, r, col in nodes:
        glow_dot(glow, x, y, r * 4 + 6, col, 95 if col != WHITE else 50)
    glow = glow.filter(ImageFilter.GaussianBlur(9))
    base = Image.alpha_composite(base, glow)
    d2 = ImageDraw.Draw(base)
    for x, y, r, col in nodes:
        d2.ellipse([x - r, y - r, x + r, y + r], fill=rgba(col, 240))
        d2.ellipse([x - r, y - r, x + r, y + r], outline=rgba(WHITE, 70), width=1)
    base.save(os.path.join(PA, "hero_network.png"))
    print("hero ok", base.size)


# ---------------------------------------------------------------- paper noise
def make_noise():
    W, H = 2362, 3543  # ~100dpi
    rnd = np.random.RandomState(3)
    n = rnd.randint(0, 256, (H, W), dtype=np.uint8)
    a = np.where(n > 200, 9, np.where(n < 40, 7, 0)).astype(np.uint8)  # sparse grain
    # vignette
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    dd = np.sqrt(((xx - cx) / (W * 0.75)) ** 2 + ((yy - cy) / (H * 0.75)) ** 2)
    vig = np.clip((dd - 0.55) * 22, 0, 14).astype(np.uint8)
    a = np.clip(a.astype(np.int16) + vig.astype(np.int16), 0, 255).astype(np.uint8)
    rgb = np.zeros((H, W, 3), dtype=np.uint8)  # black grain darkens paper subtly
    img = Image.fromarray(np.dstack([rgb, a[:, :, None]]), "RGBA")
    img.save(os.path.join(PA, "paper_noise.png"))
    print("noise ok", img.size)


# ---------------------------------------------------------------- icons (linear)
def new_icon():
    return Image.new("RGBA", (200, 200), (0, 0, 0, 0))


def draw_icon(name, color):
    im = new_icon(); d = ImageDraw.Draw(im); w = 9; c = rgba(color, 255)
    if name == "academic":
        d.line([(100, 52), (100, 150)], fill=c, width=w)
        d.arc([(34, 50), (100, 150)], start=90, end=270, fill=c, width=w)
        d.arc([(100, 50), (166, 150)], start=270, end=90, fill=c, width=w)
        d.line([(34, 50), (100, 50)], fill=c, width=w); d.line([(100, 50), (166, 50)], fill=c, width=w)
        d.line([(34, 150), (100, 150)], fill=c, width=w); d.line([(100, 150), (166, 150)], fill=c, width=w)
    elif name == "daily":
        d.rounded_rectangle([(46, 70), (132, 150)], radius=14, outline=c, width=w)
        d.arc([(120, 84), (158, 128)], start=270, end=90, fill=c, width=w)
        d.line([(58, 40), (58, 58)], fill=c, width=w - 2); d.line([(82, 36), (82, 58)], fill=c, width=w - 2); d.line([(106, 40), (106, 58)], fill=c, width=w - 2)
    elif name == "dating":
        d.ellipse([(44, 52), (100, 108)], fill=c); d.ellipse([(100, 52), (156, 108)], fill=c)
        d.polygon([(46, 92), (154, 92), (100, 150)], fill=c)
    elif name == "explain":
        d.rounded_rectangle([(34, 46), (166, 128)], radius=20, outline=c, width=w)
        d.polygon([(64, 124), (64, 156), (96, 124)], fill=c)
        d.ellipse([(70, 80), (82, 92)], fill=c); d.ellipse([(94, 80), (106, 92)], fill=c); d.ellipse([(118, 80), (130, 92)], fill=c)
    elif name == "loop":
        d.arc([(44, 44), (156, 156)], start=200, end=340, fill=c, width=w)
        d.polygon([(150, 64), (176, 70), (150, 92)], fill=c)
        d.arc([(44, 44), (156, 156)], start=20, end=160, fill=c, width=w)
        d.polygon([(50, 136), (24, 130), (50, 108)], fill=c)
    elif name == "shield":
        d.polygon([(100, 38), (156, 60), (156, 104), (100, 162), (44, 104), (44, 60)], outline=c, width=w)
        d.line([(76, 100), (94, 120), (128, 78)], fill=c, width=w)
    elif name == "chip":
        d.rounded_rectangle([(64, 64), (136, 136)], radius=10, outline=c, width=w)
        d.rounded_rectangle([(86, 86), (114, 114)], radius=4, fill=c)
        for p in (78, 100, 122):
            d.line([(p, 40), (p, 64)], fill=c, width=w - 2); d.line([(p, 136), (p, 160)], fill=c, width=w - 2)
            d.line([(40, p), (64, p)], fill=c, width=w - 2); d.line([(136, p), (160, p)], fill=c, width=w - 2)
    elif name == "scan":
        for (x0, y0, sx, sy) in [(40, 40, 1, 1), (160, 40, -1, 1), (40, 160, 1, -1), (160, 160, -1, -1)]:
            d.line([(x0, y0), (x0 + 34 * sx, y0)], fill=c, width=w); d.line([(x0, y0), (x0, y0 + 34 * sy)], fill=c, width=w)
        d.line([(52, 100), (148, 100)], fill=rgba(color, 200), width=w - 2)
    im.save(os.path.join(PA, f"icon_{name}.png"))
    return im


def make_icons():
    names = ["academic", "daily", "dating", "explain", "loop", "shield", "chip", "scan"]
    for n in names:
        draw_icon(n, PURPLE)
    print("icons ok", len(names))


# ---------------------------------------------------------------- arch infographic
def _cyl(d, x, y, w, h, fill, stroke):
    eo = h * 0.22
    d.rectangle([x, y + eo / 2, x + w, y + h - eo / 2], fill=fill, outline=None)
    d.ellipse([x, y + h - eo, x + w, y + h], fill=fill, outline=stroke, width=3)
    d.line([(x, y + eo / 2), (x, y + h - eo / 2)], fill=stroke, width=3)
    d.line([(x + w, y + eo / 2), (x + w, y + h - eo / 2)], fill=stroke, width=3)
    d.ellipse([x, y, x + w, y + eo], fill=fill, outline=stroke, width=3)


def _pill(d, x, y, w, h, text, font, fill, stroke, tcol, lw=3):
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=fill, outline=stroke, width=lw)
    tb = d.textbbox((0, 0), text, font=font); tw = tb[2] - tb[0]; th = tb[3] - tb[1]
    d.text((x + (w - tw) / 2 - tb[0], y + (h - th) / 2 - tb[1]), text, font=font, fill=tcol)


def make_arch():
    W, H = 2400, 800
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f_lab = F(MONOB_TTF, 30); f_labcn = F(SANS_TTF, 30); f_cap = F(SANS_TTF, 33)
    f_mono = F(MONO_TTF, 24); f_sub = F(SANS_TTF, 24)
    LX0, RX0 = 360, W - 60
    band_w = RX0 - LX0

    def band(top, h, fill, lab_en, lab_cn, labcol):
        d.rounded_rectangle([LX0, top, RX0, top + h], radius=26, fill=fill, outline=LINE, width=2)
        d.text((60, top + h / 2 - 34), lab_en, font=f_lab, fill=labcol)
        d.text((60, top + h / 2 + 4), lab_cn, font=f_labcn, fill=INK2)

    # layer 1 clients
    b1 = 30; bh1 = 140
    band(b1, bh1, PURPLE_LT, "CLIENTS", "接入层", PURPLE_D)
    pills1 = ["React Web", "Expo Mobile"]
    pw, ph = 360, 80; gx = LX0 + 120; gy = b1 + (bh1 - ph) / 2
    for i, t in enumerate(pills1):
        _pill(d, gx + i * (pw + 90), gy, pw, ph, t, f_cap, WHITE, PURPLE, PURPLE_D, 3)
    # layer 2 services
    b2 = 210; bh2 = 210
    band(b2, bh2, WHITE, "SERVICES", "能力层", PURPLE_D)
    pills2 = ["认证", "资料·问卷", "推荐引擎", "内容审核", "即时通讯", "邀请转发"]
    pw2, ph2 = 300, 84; cols = 3; gx2 = LX0 + 70; gy2 = b2 + 30
    for i, t in enumerate(pills2):
        r, cc = divmod(i, cols)
        x = gx2 + cc * (pw2 + 56); y = gy2 + r * (ph2 + 20)
        _pill(d, x, y, pw2, ph2, t, f_cap, WHITE, PURPLE, INK, 3)
    # layer 3 data
    b3 = 460; bh3 = 210
    band(b3, bh3, ORANGE_LT, "DATA", "数据层", ORANGE_D)
    cyls = [("PostgreSQL", "+ pgvector"), ("Redis", "会话 / 缓存"), ("MinIO / S3", "对象存储")]
    cw, ch = 300, 140; gx3 = LX0 + 90; gy3 = b3 + 38
    for i, (t1, t2) in enumerate(cyls):
        x = gx3 + i * (cw + 90)
        _cyl(d, x, gy3, cw, ch, WHITE, ORANGE_D)
        tb1 = d.textbbox((0, 0), t1, font=f_cap); d.text((x + (cw - (tb1[2] - tb1[0])) / 2, gy3 + ch * 0.32), t1, font=f_cap, fill=INK)
        tb2 = d.textbbox((0, 0), t2, font=f_sub); d.text((x + (cw - (tb2[2] - tb2[0])) / 2, gy3 + ch * 0.62), t2, font=f_sub, fill=GREY)
    # connectors
    d.line([(LX0 + band_w * 0.3, b1 + bh1), (LX0 + band_w * 0.3, b2)], fill=LINE, width=3)
    d.line([(LX0 + band_w * 0.62, b1 + bh1), (LX0 + band_w * 0.62, b2)], fill=LINE, width=3)
    for fx in (0.22, 0.5, 0.78):
        d.line([(LX0 + band_w * fx, b2 + bh2), (LX0 + band_w * fx, b3)], fill=LINE, width=3)
    # AI gateway block inside services band (right)
    ax, ay, aw, ah = RX0 - 470, b2 + 28, 430, bh2 - 56
    d.rounded_rectangle([ax, ay, ax + aw, ay + ah], radius=20, fill=PURPLE, outline=None)
    d.text((ax + 28, ay + 22), "AI 网关", font=F(SANS_TTF, 40), fill=WHITE)
    d.text((ax + 28, ay + 80), "多 Provider 兼容", font=F(SANS_TTF, 26), fill=rgba(WHITE, 220))
    d.text((ax + 28, ay + 120), "DeepSeek·Kimi·LMStudio", font=F(MONO_TTF, 22), fill=rgba(WHITE, 180))
    im.save(os.path.join(PA, "arch_infographic.png"))
    print("arch ok", im.size)


# ---------------------------------------------------------------- pipe timeline
def make_pipe():
    W, H = 2400, 560
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f_track = F(SANS_TTF, 34); f_tracken = F(MONOB_TTF, 26); f_node = F(SANS_TTF, 30); f_num = F(MONOB_TTF, 24)

    def track(y, color, col_d, label_cn, label_en, nodes):
        d.text((60, y - 70), label_cn, font=f_track, fill=col_d)
        d.text((60, y - 30), label_en, font=f_tracken, fill=color)
        x0, x1 = 430, W - 120
        n = len(nodes); step = (x1 - x0) / (n - 1)
        xs = [x0 + i * step for i in range(n)]
        d.line([(xs[0], y), (xs[-1], y)], fill=rgba(color, 120), width=4)
        for i, (x, lab) in enumerate(zip(xs, nodes)):
            up = (i % 2 == 0)
            # arrow head between nodes
            if i < n - 1:
                mx = (x + xs[i + 1]) / 2
                d.polygon([(mx - 8, y - 7), (mx + 8, y), (mx - 8, y + 7)], fill=rgba(color, 160))
            big = (i == 0 or i == n - 1)
            r = 26 if big else 18
            d.ellipse([x - r, y - r, x + r, y + r], fill=(color if big else WHITE), outline=color, width=5)
            d.text((x - 7, y - 13), str(i + 1), font=f_num, fill=(WHITE if big else color))
            tb = d.textbbox((0, 0), lab, font=f_node); tw = tb[2] - tb[0]
            ly = y - r - 50 if up else y + r + 16
            d.text((x - tw / 2, ly), lab, font=f_node, fill=INK)

    track(170, PURPLE, PURPLE_D, "推荐链", "RECOMMEND",
          ["向量召回", "规则打分", "Two-Tower", "MMR 重排", "AI 解释"])
    track(410, ORANGE, ORANGE_D, "微调链", "FINETUNE",
          ["用户反馈", "SFT / DPO", "QLoRA 微调", "导出 GGUF"])
    im.save(os.path.join(PA, "pipe_timeline.png"))
    print("pipe ok", im.size)


# ---------------------------------------------------------------- device mockups
def _shadow(size, off=(14, 22), blur=26, alpha=110):
    sh = Image.new("RGBA", (size[0] + 160, size[1] + 160), (0, 0, 0, 0))
    dd = ImageDraw.Draw(sh)
    dd.rounded_rectangle([80 + off[0], 80 + off[1], 80 + off[0] + size[0], 80 + off[1] + size[1]],
                         radius=28, fill=(10, 10, 14, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    return sh, (80, 80)


def make_browser(shot_path, out_name, width=1480, crop=1.0):
    src = Image.open(shot_path).convert("RGB")
    if crop < 1.0:
        src = src.crop((0, 0, src.width, int(src.height * crop)))
    bar = 64; pad = 0
    iw = width; ih = int(src.height * iw / src.width)
    src = src.resize((iw, ih), Image.LANCZOS)
    body_h = ih
    W = iw; H = bar + body_h
    win = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(win)
    d.rounded_rectangle([0, 0, W, H], radius=22, fill=WHITE)
    d.rounded_rectangle([0, 0, W, bar], radius=22, fill=(238, 238, 242))
    d.rectangle([0, bar - 22, W, bar], fill=(238, 238, 242))
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([22 + i * 30, bar / 2 - 9, 22 + i * 30 + 18, bar / 2 + 9], fill=col)
    # address bar
    d.rounded_rectangle([150, bar / 2 - 16, W - 150, bar / 2 + 16], radius=16, fill=WHITE, outline=LINE, width=2)
    d.text((172, bar / 2 - 12), "skdmatch.app", font=F(MONO_TTF, 22), fill=GREY)
    win.paste(src, (0, bar))
    # clip bottom corners
    mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, W, H], radius=22, fill=255)
    win.putalpha(mask)
    sh, off = _shadow((W, H))
    canvas = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, sh)
    canvas.paste(win, off, win)
    canvas.save(os.path.join(PA, out_name))
    print("browser ok", out_name, canvas.size)


def make_phone(shot_path, out_name, width=560):
    src = Image.open(shot_path).convert("RGB")
    bezel = 26; notch_h = 40; rad = 64
    iw = width - 2 * bezel; ih = int(src.height * iw / src.width)
    src = src.resize((iw, ih), Image.LANCZOS)
    W = width; H = ih + 2 * bezel
    ph = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ph)
    d.rounded_rectangle([0, 0, W, H], radius=rad, fill=INK2)
    # screen mask
    scr = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    scr.paste(src, (0, 0))
    sm = Image.new("L", (iw, ih), 0); ImageDraw.Draw(sm).rounded_rectangle([0, 0, iw, ih], radius=rad - 14, fill=255)
    scr.putalpha(sm)
    ph.paste(scr, (bezel, bezel), scr)
    # notch
    d.rounded_rectangle([W / 2 - 70, bezel - 4, W / 2 + 70, bezel + notch_h], radius=18, fill=INK2)
    sh, off = _shadow((W, H), off=(12, 20), blur=24, alpha=120)
    canvas = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, sh)
    canvas.paste(ph, off, ph)
    canvas.save(os.path.join(PA, out_name))
    print("phone ok", out_name, canvas.size)


def make_devices():
    make_browser(os.path.join(SHOTS, "landing.png"), "shot_browser.png", 1500, crop=0.62)
    make_phone(os.path.join(SHOTS, "profile.png"), "shot_phone1.png", 560)
    make_phone(os.path.join(SHOTS, "questionnaire_basic.png"), "shot_phone2.png", 520)


# ---------------------------------------------------------------- assets entry
def build_assets():
    make_hero(); make_noise(); make_icons(); make_arch(); make_pipe(); make_devices()
    print("ALL ASSETS DONE")


# ================================================================ reportlab build
def build_pdf():
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import ImageReader
    from PIL import Image as PILImage

    pdfmetrics.registerFont(TTFont('SerifCJK', SERIF_TTF))
    pdfmetrics.registerFont(TTFont('SansCJK', SANS_TTF))
    pdfmetrics.registerFont(TTFont('SansCJKB', SANS_TTF))
    pdfmetrics.registerFont(TTFont('Mono', MONO_TTF))
    pdfmetrics.registerFont(TTFont('MonoB', MONOB_TTF))

    INKc = HexColor("#101015"); PAPERc = HexColor("#F6F4EE"); PURPLEc = HexColor("#7C3AED")
    ORANGEc = HexColor("#F97316"); MUTED = HexColor("#96969A"); LINED = HexColor("#6B6B78")
    HAIR = HexColor("#D9D5C9"); PURPLELTc = HexColor("#EDE9FE"); ORANGELTc = HexColor("#FFEDD5")
    INKSOFT = HexColor("#26262E")

    WCM, HCM = 60.0, 90.0; W, H = WCM * cm, HCM * cm; LM, RM = 3.4, 3.4; RX = WCM - RM

    def tx(x): return x * cm
    def ty(t): return (HCM - t) * cm
    def mixed(x, y, segs):
        cx = x
        for t, f, s, col in segs:
            c.setFont(f, s); c.setFillColor(col); c.drawString(cx, y, t); cx += pdfmetrics.stringWidth(t, f, s)
        return cx
    def mixed_r(rx, y, segs):
        tot = sum(pdfmetrics.stringWidth(t, f, s) for t, f, s, _ in segs); return mixed(rx - tot, y, segs)
    def img(name): return ImageReader(os.path.join(PA, name))
    def psize(name):
        return PILImage.open(os.path.join(PA, name)).size
    def draw_img_fit(name, x_cm, top_cm, w_cm, h_cm):
        iw, ih = psize(name); ar = iw / ih
        if w_cm / h_cm > ar:
            hh = h_cm; ww = hh * ar
        else:
            ww = w_cm; hh = ww / ar
        xx = x_cm + (w_cm - ww) / 2; yyt = top_cm + (h_cm - hh) / 2
        c.drawImage(img(name), tx(xx), ty(yyt + hh), ww * cm, hh * cm, mask='auto')
        return xx, yyt, ww, hh

    c = canvas.Canvas(OUT_PDF, pagesize=(W, H)); c.setTitle("SKDMatch 海报 · c-4 Philia")
    # paper bg
    c.setFillColor(PAPERc); c.rect(0, 0, W, H, fill=1, stroke=0)

    # ---------- masthead 0~20
    HEAD = 20.0
    c.setFillColor(INKc); c.rect(0, ty(HEAD), W, HEAD * cm, fill=1, stroke=0)
    # fine grid on dark
    c.setStrokeColor(HexColor("#26262E")); c.setLineWidth(0.6)
    gx = 2.0
    while gx < WCM:
        c.line(tx(gx), ty(HEAD), tx(gx), ty(0)); gx += 2.0
    gy = 2.0
    while gy < HEAD:
        c.line(tx(0), ty(gy), tx(WCM), ty(gy)); gy += 2.0
    # hero network on right
    hiw, hih = psize("hero_network.png"); har = hiw / hih
    hh_cm = 17.0; ww_cm = hh_cm * har
    c.drawImage(img("hero_network.png"), tx(WCM - ww_cm - 0.5), ty(1.5 + hh_cm), ww_cm * cm, hh_cm * cm, mask='auto')
    # faint 缘 behind title-left? keep one subtle char top-right under network
    c.saveState(); c.setFillColor(white); c.setFillAlpha(0.04); c.setFont('SerifCJK', 300)
    c.drawString(tx(WCM - 22), ty(15.5), "缘"); c.restoreState()
    # top-left label
    mixed(tx(LM), ty(2.7), [("FINALS 2026  ·  c-4  ·  TRACK ", 'MonoB', 17, MUTED), ("生活娱乐伙伴", 'SansCJKB', 17, white)])
    # brand bars
    c.setFillColor(PURPLEc); c.rect(tx(LM), ty(3.7), 3.0 * cm, 0.34 * cm, fill=1, stroke=0)
    c.setFillColor(ORANGEc); c.rect(tx(LM + 3.15), ty(3.7), 1.5 * cm, 0.34 * cm, fill=1, stroke=0)
    # title with letter spacing (draw char by char)
    def spaced(text, x_cm, y_cm, font, size, col, sp):
        cx = x_cm
        c.setFont(font, size); c.setFillColor(col)
        for ch in text:
            c.drawString(tx(cx), ty(y_cm), ch); cx += pdfmetrics.stringWidth(ch, font, size) / cm + sp
        return cx
    spaced("SKDMatch", LM - 0.2, 11.4, 'SerifCJK', 150, white, 0.06)
    mixed(tx(LM), ty(14.6), [("科爱捏", 'SerifCJK', 60, ORANGEc), ("   上科大校内互助交流平台", 'SansCJKB', 32, white)])
    # tilted sticker label
    c.saveState(); sx, sy = tx(LM + 0.2), ty(16.7); c.translate(sx, sy); c.rotate(-4)
    c.setFillColor(ORANGEc); c.roundRect(0, -0.95 * cm, 13.2 * cm, 1.5 * cm, 0.18 * cm, fill=1, stroke=0)
    c.setFillColor(white); c.setFont('SansCJKB', 26); c.drawString(0.5 * cm, -0.5 * cm, "上科大 · 2026 决赛路演")
    c.restoreState()
    # right github + team
    mixed_r(tx(RX), ty(18.4), [("github.com/tzhazuma/STUMatch", 'Mono', 15, MUTED)])
    mixed_r(tx(RX), ty(19.1), [("TEAM  ", 'MonoB', 14.5, ORANGEc), ("唐志昊 / 司雪阳 / 唐玟", 'SansCJKB', 15.5, white)])

    # ---------- section title helper
    def sec(top, num, title, en, col):
        x = tx(LM)
        c.setFont('MonoB', 56); c.setFillColor(col); c.drawString(x, ty(top + 1.7), num)
        nw = pdfmetrics.stringWidth(num, 'MonoB', 56)
        c.setFillColor(INKc); c.setFont('SerifCJK', 52); c.drawString(x + nw + 0.5 * cm, ty(top + 1.65), title)
        tw = pdfmetrics.stringWidth(title, 'SerifCJK', 52)
        c.setFillColor(LINED); c.setFont('MonoB', 22); c.drawString(x + nw + 0.5 * cm + tw + 0.6 * cm, ty(top + 1.45), en)
        c.setStrokeColor(col); c.setLineWidth(3.0); c.line(x, ty(top + 2.45), x + 4.2 * cm, ty(top + 2.45))
        c.setStrokeColor(HAIR); c.setLineWidth(1.0); c.line(x + 4.2 * cm, ty(top + 2.45), tx(RX), ty(top + 2.45))

    # ---------- A scenes 20.5~31
    sec(20.6, "01", "三大匹配场景", "THREE SCENES", PURPLEc)
    # left big card academic
    lx, lt, lw, lh = LM, 23.6, 26.0, 7.0
    c.setFillColor(PURPLELTc); c.setStrokeColor(PURPLEc); c.setLineWidth(2.2)
    c.roundRect(tx(lx), ty(lt + lh), lw * cm, lh * cm, 0.4 * cm, fill=1, stroke=1)
    c.setFillColor(PURPLEc); c.rect(tx(lx), ty(lt + lh), 0.34 * cm, lh * cm, fill=1, stroke=0)
    c.drawImage(img("icon_academic.png"), tx(lx + lw - 3.4), ty(lt + 3.2), 2.6 * cm, 2.6 * cm, mask='auto')
    mixed(tx(lx + 1.1), ty(lt + 2.2), [("学术交流", 'SerifCJK', 42, INKc), ("  ACADEMIC", 'MonoB', 17, PURPLEc)])
    c.setFont('SansCJKB', 24); c.setFillColor(INKc)
    c.drawString(tx(lx + 1.1), ty(lt + 3.9), "找同方向研究伙伴，")
    c.drawString(tx(lx + 1.1), ty(lt + 5.0), "组队做项目、聊课题。")
    c.setFont('Mono', 15); c.setFillColor(LINED); c.drawString(tx(lx + 1.1), ty(lt + 6.3), "// research-partner matching")
    # right two cards
    rx0 = 31.0; rw = RX - rx0
    def small_card(top, h, name, en, col, icon, desc):
        c.setFillColor(white); c.setStrokeColor(HAIR); c.setLineWidth(1.4)
        c.roundRect(tx(rx0), ty(top + h), rw * cm, h * cm, 0.34 * cm, fill=1, stroke=1)
        c.setFillColor(col); c.rect(tx(rx0), ty(top + h), 0.30 * cm, h * cm, fill=1, stroke=0)
        c.drawImage(img(icon), tx(rx0 + rw - 3.0), ty(top + 2.5), 2.0 * cm, 2.0 * cm, mask='auto')
        mixed(tx(rx0 + 0.9), ty(top + 1.5), [(name, 'SerifCJK', 32, INKc), ("  " + en, 'MonoB', 14, col)])
        c.setFont('SansCJKB', 20); c.setFillColor(INKc); c.drawString(tx(rx0 + 0.9), ty(top + 2.7), desc)
    small_card(23.6, 3.3, "日常生活", "DAILY", ORANGEc, "icon_daily.png", "饭搭子 · 运动伙伴 · 自习室友")
    small_card(27.3, 3.3, "恋爱交友", "DATING", PURPLEc, "icon_dating.png", "基于问卷与兴趣的真实匹配")

    # ---------- B highlights 31.5~49  (2x3 magazine grid)
    sec(31.4, "02", "六个创新亮点", "SIX HIGHLIGHTS", ORANGEc)
    hl = [
        ("三板块垂直匹配", "学术 / 生活 / 恋爱分场景独立推荐，互不干扰。", "icon_academic.png", PURPLEc),
        ("AI 可解释推荐", "为每次匹配生成“为什么推荐 TA”的理由。", "icon_explain.png", ORANGEc),
        ("问卷即画像", "问卷答案自动同步到 Profile，无需重复填写。", "icon_scan.png", PURPLEc),
        ("推荐反馈闭环", "like / skip 时间衰减 + 离线重训练持续优化。", "icon_loop.png", ORANGEc),
        ("全链路敏感词审核", "DFA + 归一化 + 动态词库，聊天留言全过滤。", "icon_shield.png", PURPLEc),
        ("本地 QLoRA 微调", "本地微调 Qwen2.5，数据不出校、保护隐私。", "icon_chip.png", ORANGEc),
    ]
    g_top = 34.0; cell_w = (RX - LM) / 2; cell_h = 4.3; gap = 0.5
    for i, (t, desc, icon, col) in enumerate(hl):
        r, cc = divmod(i, 2)
        x = LM + cc * cell_w; top = g_top + r * cell_h
        ix = x + 0.2; iy = top + 0.2; iw = cell_w - 0.4; ih = cell_h - 0.45
        c.setFillColor(white); c.setStrokeColor(HAIR); c.setLineWidth(1.2)
        c.roundRect(tx(ix), ty(iy + ih), iw * cm, ih * cm, 0.3 * cm, fill=1, stroke=1)
        c.setFillColor(col); c.rect(tx(ix), ty(iy + ih), 0.26 * cm, ih * cm, fill=1, stroke=0)
        # big faint number watermark
        c.saveState(); c.setFillColor(HexColor("#ECEAE2")); c.setFont('MonoB', 92)
        c.drawString(tx(ix + iw - 4.4), ty(iy + 3.0), "%02d" % (i + 1)); c.restoreState()
        c.drawImage(img(icon), tx(ix + 0.7), ty(iy + 2.5), 2.1 * cm, 2.1 * cm, mask='auto')
        c.setFillColor(INKc); c.setFont('SansCJKB', 28); c.drawString(tx(ix + 3.2), ty(iy + 1.7), t)
        c.setFillColor(LINED); c.setFont('SansCJK', 19); c.drawString(tx(ix + 3.2), ty(iy + 2.95), desc)
        # vertical grid line between columns
    c.setStrokeColor(HAIR); c.setLineWidth(1.0)
    c.line(tx(LM + cell_w), ty(g_top), tx(LM + cell_w), ty(g_top + 3 * cell_h - 0.45))

    # ---- image placement helpers (fit preserving aspect) ----
    def _fit(name, w_cm, h_cm):
        iw, ih = psize(name); ar = iw / ih
        if w_cm / h_cm > ar:
            hh = h_cm; ww = hh * ar
        else:
            ww = w_cm; hh = ww / ar
        return ww, hh

    def card_img(name, x_cm, top_cm, w_cm, h_cm, pad=0.3):
        ww, hh = _fit(name, w_cm, h_cm)
        xx = x_cm + (w_cm - ww) / 2; yyt = top_cm + (h_cm - hh) / 2
        c.setFillColor(white); c.setStrokeColor(HAIR); c.setLineWidth(1.2)
        c.roundRect(tx(xx - pad), ty(yyt + hh + pad), (ww + 2 * pad) * cm, (hh + 2 * pad) * cm, 0.3 * cm, fill=1, stroke=1)
        c.drawImage(img(name), tx(xx), ty(yyt + hh), ww * cm, hh * cm, mask='auto')
        return xx, yyt, ww, hh

    def plain_img(name, x_cm, top_cm, w_cm, h_cm):
        ww, hh = _fit(name, w_cm, h_cm)
        xx = x_cm + (w_cm - ww) / 2; yyt = top_cm + (h_cm - hh) / 2
        c.drawImage(img(name), tx(xx), ty(yyt + hh), ww * cm, hh * cm, mask='auto')
        return xx, yyt, ww, hh

    # ---------- C tech 47~71
    sec(47.4, "03", "技术架构与流水线", "ARCHITECTURE", PURPLEc)
    mixed(tx(LM), ty(50.2), [("向量召回→规则分→Two-Tower→MMR→AI 解释", 'SansCJKB', 19, INKc),
                              ("   ｜   ", 'SansCJKB', 19, LINED),
                              ("反馈→SFT/DPO→QLoRA→GGUF", 'SansCJKB', 19, PURPLEc)])
    card_img("arch_infographic.png", LM, 51.0, RX - LM, 12.0)
    card_img("pipe_timeline.png", LM, 63.6, RX - LM, 7.0)

    # ---------- D showcase 71~85
    sec(71.4, "04", "产品橱窗", "PRODUCT", ORANGEc)
    bx, by, bw, bh = plain_img("shot_browser.png", LM, 74.2, 25.0, 10.2)
    plain_img("shot_phone2.png", 38.0, 74.8, 8.0, 9.6)
    plain_img("shot_phone1.png", 47.5, 74.0, 8.8, 10.6)
    # annotation sticker over browser top-right
    c.saveState()
    stx, sty = tx(bx + bw - 9.0), ty(by + 1.0)
    c.setStrokeColor(PURPLEc); c.setLineWidth(2.4)
    c.roundRect(stx - 0.3 * cm, sty - 0.25 * cm, 8.6 * cm, 1.3 * cm, 0.5 * cm, fill=0, stroke=1)
    c.setFillColor(PURPLEc); c.setFont('SansCJKB', 22); c.drawString(stx, sty + 0.12 * cm, "实时匹配 · 可解释")
    c.restoreState()

    # ---------- E footer 85~90
    c.setStrokeColor(HAIR); c.setLineWidth(1.3); c.line(tx(LM), ty(85.2), tx(RX), ty(85.2))
    qr = os.path.join(ASSETS, "qr.png"); qs = 3.4; qx = LM; qt = 85.7
    tw_, th_ = qs + 1.5, qs + 0.8
    c.setFillColor(white); c.setStrokeColor(INKc); c.setLineWidth(2.6)
    c.roundRect(tx(qx), ty(qt + th_), tw_ * cm, th_ * cm, 0.2 * cm, fill=1, stroke=1)
    c.setFillColor(PAPERc)
    for k in range(7):
        c.circle(tx(qx), ty(qt + 0.4 + k * (th_ - 0.8) / 6), 0.16 * cm, fill=1, stroke=0)
    c.drawImage(ImageReader(qr), tx(qx + 0.75), ty(qt + qs + 0.4), qs * cm, qs * cm, mask='auto')
    c.setFillColor(ORANGEc); c.rect(tx(qx + tw_ - 2.1), ty(qt + 0.62), 2.1 * cm, 0.62 * cm, fill=1, stroke=0)
    c.setFillColor(white); c.setFont('MonoB', 13); c.drawCentredString(tx(qx + tw_ - 1.05), ty(qt + 0.44), "SCAN ME")
    mixed(tx(qx + tw_ + 1.0), ty(qt + 1.4), [("扫码体验 ", 'SansCJKB', 26, INKc), ("SKDMatch · 科爱捏", 'SerifCJK', 26, PURPLEc)])
    c.setFont('Mono', 15); c.setFillColor(LINED); c.drawString(tx(qx + tw_ + 1.0), ty(qt + 2.6), "github.com/tzhazuma/STUMatch")
    c.setFont('SansCJK', 17); c.setFillColor(LINED); c.drawString(tx(qx + tw_ + 1.0), ty(qt + 3.7), "学术 · 生活 · 交友  三大场景精准匹配")
    mixed_r(tx(RX), ty(qt + 1.3), [("TEAM c-4 · Philia", 'MonoB', 22, INKc)])
    mixed_r(tx(RX), ty(qt + 2.5), [("赛道 ", 'SansCJKB', 20, LINED), ("生活娱乐伙伴", 'SansCJKB', 20, PURPLEc)])
    mixed_r(tx(RX), ty(qt + 3.6), [("上海科技大学", 'SansCJKB', 20, INKc)])

    # paper noise overlay (very subtle)
    c.saveState(); c.setFillAlpha(1.0)
    c.drawImage(img("paper_noise.png"), 0, 0, W, H, mask='auto', preserveAspectRatio=False)
    c.restoreState()

    c.showPage(); c.save()
    print("WROTE", OUT_PDF)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg in ("assets", "all"):
        build_assets()
    if arg in ("build", "all"):
        build_pdf()
