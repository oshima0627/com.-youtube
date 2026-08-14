# -*- coding: utf-8 -*-
"""切り出した区間を投稿用の動画に書き出す。

ショートは 16:9 の素材を 9:16 に収める必要がある。中央を切り抜くと画面端の
人物が落ちるため、背景にぼかした全体像を敷き、前景に原寸を重ねる方式を採る。
"""

import subprocess
from pathlib import Path

from . import config, transcript

SHORT_FILTER = (
    "[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
    "crop={w}:{h},boxblur=30:2[bg];"
    "[0:v]scale={w}:-2[fg];"
    "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
)

SUB_STYLE_SHORT = (
    "FontName=Yu Gothic UI,FontSize=17,Bold=1,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00202020,BorderStyle=1,Outline=3,Shadow=1,"
    "Alignment=2,MarginV=90"
)
SUB_STYLE_WIDE = (
    "FontName=Yu Gothic UI,FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00202020,BorderStyle=1,Outline=3,Shadow=1,"
    "Alignment=2,MarginV=40"
)


def _srt_time(seconds):
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, start, end, dest: Path):
    """区間内の字幕を、区間先頭を 0 とした SRT にする。

    自動字幕は同じ文が連続して出ることがあるため、直前と同一のものは落とす。
    """
    lines, n, prev = [], 0, None
    for s in transcript.slice_segments(segments, start, end):
        text = s["text"].strip()
        if not text or text == prev or text.startswith("["):
            prev = text
            continue
        prev = text
        n += 1
        lines += [
            str(n),
            f"{_srt_time(s['start'] - start)} --> {_srt_time(min(s['end'], end) - start)}",
            text,
            "",
        ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


def _ffmpeg(args, cwd):
    r = subprocess.run(["ffmpeg", "-y", *args], capture_output=True,
                       encoding="utf-8", errors="replace", cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg が失敗しました:\n{r.stderr.strip()[-2500:]}")


def render_short(src: Path, dest: Path, srt: Path = None, overlay: Path = None):
    """9:16。背景はぼかした全体像、前景に原寸を中央配置する。

    srt は既定で焼き込まない。コムドットの本編は字幕が既に焼き込まれており、
    重ねると二重字幕になる。素材側に字幕が無い場合だけ srt を渡す。

    overlay に透過PNGを渡すと、上下のぼかし帯に情報を載せる。画面の約68%が
    死角なので、ここに元動画に無い文脈を置くのが独自性の実体になる。
    """
    fmt = config.settings()["formats"]["short"]
    vf = SHORT_FILTER.format(w=fmt["width"], h=fmt["height"])
    last = "[v]"
    if srt:
        vf += f";{last}subtitles={srt.name}:force_style='{SUB_STYLE_SHORT}'[s]"
        last = "[s]"

    inputs = ["-i", src.name]
    if overlay:
        inputs += ["-i", overlay.name]
        vf += f";{last}[1:v]overlay=0:0[out]"
        last = "[out]"

    _ffmpeg([*inputs, "-filter_complex", vf, "-map", last, "-map", "0:a",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k", dest.name], cwd=src.parent)
    return dest


def render_wide(src: Path, dest: Path, srt: Path = None):
    """16:9。既定では素材のまま。字幕の扱いは render_short と同じ。"""
    fmt = config.settings()["formats"]["wide"]
    vf = (f"scale={fmt['width']}:{fmt['height']}:force_original_aspect_ratio=decrease,"
          f"pad={fmt['width']}:{fmt['height']}:(ow-iw)/2:(oh-ih)/2")
    if srt:
        vf += f",subtitles={srt.name}:force_style='{SUB_STYLE_WIDE}'"
    _ffmpeg(["-i", src.name, "-vf", vf,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k", dest.name], cwd=src.parent)
    return dest
