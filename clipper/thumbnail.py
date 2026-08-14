# -*- coding: utf-8 -*-
"""サムネイルを作る。

素材はクリップ本編から抜いたフレーム。切り抜きとして出せる映像なら、その
1コマも同じ範囲に収まる。ロゴは使わない（権利者のロゴ利用は一般に禁じられる）。

文字は hook をそのまま使う。動画の上帯と同じ文言にして、見た人が「同じもの」
だと分かるようにする。
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from . import config, overlay

WIDTH, HEIGHT = 1280, 720

INK = (18, 18, 20)
PAPER = (255, 255, 255)
ACCENT = (230, 30, 45)


def grab_frame(src: Path, at: float, dest: Path):
    """指定秒のフレームを 16:9 で抜く。"""
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", str(at), "-i", str(src), "-frames:v", "1",
         "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{HEIGHT}", str(dest)],
        capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not dest.exists():
        raise RuntimeError(f"フレームを抜けませんでした:\n{r.stderr.strip()[-800:]}")
    return dest


def compose(frame_path: Path, hook, dest: Path):
    """フレームの下側に帯を敷き、hook を大きく載せる。

    人物の顔は上寄りに写ることが多いので、文字は下に置いて顔を潰さない。
    """
    img = Image.open(frame_path).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")

    if not hook:
        img.save(dest)
        return dest

    f = overlay.font(72)
    lines = overlay.wrap(d, hook, f, WIDTH - 110)
    block_h = len(lines) * f.size + (len(lines) - 1) * 16

    # 帯は不透明にする。半透明だと元動画の焼き込みテロップが透けて重なり、
    # こちらの文字と両方読めなくなる（実際にそうなった）。
    band_top = HEIGHT - block_h - 96
    d.rectangle([0, band_top, WIDTH, HEIGHT], fill=(0, 0, 0, 255))
    d.rectangle([0, band_top, WIDTH, band_top + 8], fill=ACCENT)

    y = band_top + 44
    for line in lines:
        w = d.textlength(line, font=f)
        d.text((WIDTH / 2 - w / 2, y), line, font=f, fill=PAPER,
               stroke_width=5, stroke_fill=INK)
        y += f.size + 16

    img.save(dest)
    return dest


def build_for_clip(video_id, clip, at=None):
    """クリップの中ほどのフレームからサムネイルを作る。

    冒頭は前の場面から切り替わった直後で人物が定まっていないことが多いので、
    既定では区間の 40% 地点を使う。
    """
    wd = config.work_dir(video_id)
    src = wd / f"{clip['clip_id']}_src.mp4"
    if not src.exists():
        raise RuntimeError(f"{src} がありません")

    length = clip["end"] - clip["start"]
    at = at if at is not None else length * 0.4
    frame = grab_frame(src, at, wd / f"{clip['clip_id']}_frame.png")
    return compose(frame, clip.get("hook"), wd / f"{clip['clip_id']}_thumb.png")
