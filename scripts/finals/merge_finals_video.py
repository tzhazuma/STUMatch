#!/usr/bin/env python3
"""Merge the SKDMatch finals demo video, optionally inserting a LIVE recording.

Self-contained: rebuilds the screenshot slideshow from ROOT/screenshots (dark
background + floating card + step number + Chinese caption), then concatenates
intro + slideshow + [optional live webm] + outro with crossfades.

Usage:
  # rebuild the existing slideshow-only video (no live part) -> safe dry run:
  python3 scripts/finals/merge_finals_video.py --out /tmp/merge_check.mp4

  # after you recorded a live webm (see record_live_demo.py), insert it BEFORE
  # the outro and overwrite the deliverable:
  python3 scripts/finals/merge_finals_video.py --webm /tmp/record_vid/xxx.webm \
      --out finals/c-4_SKDMatch.mp4

Hard cap: total duration <= 180s (the live part is truncated/sped-up if needed).
"""
import argparse, os, glob, subprocess, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = "/mnt/c/Users/tzh03/Downloads/STUMatch2/STUMatch"


def _first(*paths):
    for p in paths:
        if os.path.isdir(p):
            return p
    return paths[0]


ASSETS = _first(os.path.join(ROOT, "finals_assets"), os.path.join(ROOT, "finals", "finals_assets"))
SHOTS = _first(os.path.join(ROOT, "screenshots"), os.path.join(ROOT, "finals", "screenshots"))
W, H = 1280, 720
INK = (16, 16, 21)
PURPLE = (124, 58, 237)
ORANGE = (247, 115, 22)
MUTED = (150, 150, 162)
FADE = 0.5
MAX_TOTAL = 178.0

SANS_B = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0)
MONO_B = ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 0)

# (screenshot file, caption, duration seconds)  -- order == playback order
SEQ = [
    ("landing.png",            "品牌落地页 · 学术/生活/恋爱 三大匹配场景", 9),
    ("login.png",              "邮箱白名单认证 · 安全登录", 7),
    ("register.png",           "注册 · 服务协议与隐私政策同意", 6),
    ("discovery_academic.png", "学术交流 · 智能推荐与匹配分", 10),
    ("discovery_daily.png",    "日常生活 · 兴趣搭子匹配", 7),
    ("discovery_dating.png",   "恋爱交友 · 缘分匹配", 7),
    ("user_detail.png",        "候选人详情 · 匹配理由与标签", 7),
    ("questionnaire_basic.png","问卷即画像 · 进阶问卷填写", 9),
    ("profile.png",            "个人资料 · 邀请码转发好友", 9),
    ("friends.png",            "好友管理 · 申请与接受", 6),
    ("chat.png",               "实时聊天 · WebSocket 消息", 8),
]


def font(spec, size):
    return ImageFont.truetype(spec[0], size, index=spec[1])


def build_frame(png_path, idx, total, caption, out_path):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img, "RGBA")
    shot = Image.open(png_path).convert("RGB")
    # fit into a centered box with margins
    box_w, box_h = W - 240, H - 200
    r = min(box_w / shot.width, box_h / shot.height)
    nw, nh = int(shot.width * r), int(shot.height * r)
    shot = shot.resize((nw, nh), Image.LANCZOS)
    x = (W - nw) // 2
    y = 70 + (box_h - nh) // 2
    # drop shadow (offset dark rect) then thin border then image
    d.rectangle([(x + 8, y + 10), (x + nw + 8, y + nh + 10)], fill=(0, 0, 0, 120))
    d.rectangle([(x - 2, y - 2), (x + nw + 2, y + nh + 2)], fill=(60, 60, 70, 255))
    img.paste(shot, (x, y))
    # top brand double bar (left)
    d.rectangle([(56, 30), (116, 38)], fill=(*PURPLE, 255))
    d.rectangle([(116, 30), (150, 38)], fill=(*ORANGE, 255))
    # top-right step number (mono, ascii-only -> safe)
    step = f"{idx:02d} / {total:02d}"
    f_mono = font(MONO_B, 22)
    sw = d.textlength(step, font=f_mono)
    d.text((W - 56 - sw, 24), step, font=f_mono, fill=(*MUTED, 255))
    # bottom caption bar
    bar_h = 78
    d.rectangle([(0, H - bar_h), (W, H)], fill=(8, 8, 12, 230))
    d.rectangle([(56, H - bar_h + 22), (62, H - 22)], fill=(*ORANGE, 255))  # accent tick
    f_cap = font(SANS_B, 26)  # Chinese caption -> CJK font (no tofu)
    d.text((80, H - bar_h + 24), caption, font=f_cap, fill=(246, 244, 238, 255))
    img.save(out_path)


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def make_clip(png_path, dur, out_mp4):
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", png_path,
                    "-vf", "fps=30,scale=1280:720:force_original_aspect_ratio=decrease,"
                           "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x101015,setsar=1,format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", out_mp4],
                   check=True, capture_output=True)


def normalize_webm(webm, cap, speed, out_mp4):
    vf = (f"fps=30,setpts={(1.0/speed):.4f}*PTS,"
          f"scale=1280:720:force_original_aspect_ratio=decrease,"
          f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x101015,setsar=1,format=yuv420p,"
          f"drawbox=x=24:y=24:w=16:h=16:color=0xF97316:t=fill")
    subprocess.run(["ffmpeg", "-y", "-i", webm, "-t", str(cap),
                    "-vf", vf, "-an",
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", out_mp4],
                   check=True, capture_output=True)


def xfade_concat(clips, durs, out_mp4):
    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", c]
    filt = []
    for i in range(len(clips)):
        filt.append(f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
    prev = "v0"
    for k in range(1, len(clips)):
        offset = sum(durs[:k]) - FADE * k
        out = f"x{k}" if k < len(clips) - 1 else "vout"
        filt.append(f"[{prev}][v{k}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[{out}]")
        prev = out
    cmd += ["-filter_complex", ";".join(filt), "-map", "[vout]", "-an",
            "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", out_mp4]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("xfade failed: " + r.stderr[-1500:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--webm", default=None, help="optional live recording webm to insert before outro")
    ap.add_argument("--out", default="/tmp/merge_out.mp4")
    ap.add_argument("--speed", type=float, default=1.0, help="speed-up factor for the live part")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="merge_vid_")
    try:
        # build slideshow frames
        frame_pngs, frame_durs = [], []
        for i, (fn, cap, dur) in enumerate(SEQ, 1):
            fp = os.path.join(tmp, f"frame_{i:02d}.png")
            build_frame(os.path.join(SHOTS, fn), i, len(SEQ), cap, fp)
            frame_pngs.append(fp); frame_durs.append(dur)

        intro = os.path.join(ASSETS, "intro.png")
        outro = os.path.join(ASSETS, "outro.png")

        # assemble order + durations
        order_pngs = [intro] + frame_pngs + [outro]
        durs = [3.5] + frame_durs + [3.5]
        live_clip = None
        if args.webm:
            d_real = probe_dur(args.webm)
            # budget left for live so total <= MAX_TOTAL
            base_total = sum(durs) - (len(durs) - 1) * FADE  # without live, with its 2 boundary xfades counted later
            # with live inserted we add 1 segment and 1 extra xfade boundary
            spare = MAX_TOTAL - (base_total - FADE)  # base_total already had intro-slides-outro = 2 xfades; with live =3 -> subtract one more FADE from base when computing? keep simple:
            live_cap = max(4.0, min(d_real / args.speed, MAX_TOTAL - base_total + FADE - 1.0))
            live_clip = os.path.join(tmp, "live.mp4")
            normalize_webm(args.webm, live_cap, args.speed, live_clip)
            live_dur = probe_dur(live_clip)
            # insert before outro
            order_pngs = [intro] + frame_pngs + [live_clip] + [outro]
            durs = [3.5] + frame_durs + [live_dur] + [3.5]

        # make a clip per png (live already a clip)
        clips, clip_durs = [], []
        for i, item in enumerate(order_pngs):
            if item == live_clip:
                clips.append(live_clip); clip_durs.append(durs[i]); continue
            mp4 = os.path.join(tmp, f"clip_{i:02d}.mp4")
            make_clip(item, durs[i], mp4)
            clips.append(mp4); clip_durs.append(durs[i])

        xfade_concat(clips, clip_durs, args.out)
        final = probe_dur(args.out)
        print("OUT=" + args.out)
        print("DURATION=%.2f" % final)
        print("HAS_LIVE=" + ("yes" if args.webm else "no"))
        print("SIZE=%d" % os.path.getsize(args.out))
        assert final <= 180.0, "exceeded 180s!"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
