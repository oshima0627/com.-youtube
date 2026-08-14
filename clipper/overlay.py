# -*- coding: utf-8 -*-
"""ショートの上下の帯に置く情報を、透過PNGとして作る。

9:16 に収めた 16:9 の映像は、画面の約68%がぼかしの死角になる
（1920px のうち映像は 608px）。そこに**元動画に無い情報**を置く。

置くのは文脈の説明に限る。企画のルール、直前に何が起きたか、といった
「切り抜きから入った人が知らない前提」を補う。**笑いを足す書き込みや、
元の意図と違う印象を与える文言は入れない。** 出演者の名誉を害する編集に
あたりうるため。

ffmpeg の drawtext は Windows でフォントパスのエスケープが壊れやすく、
日本語の折り返しも自前になる。Pillow で作った PNG を overlay するほうが
字形と改行を完全に制御できる。
"""

from PIL import Image, ImageDraw, ImageFont

from . import config

FONT_PATH = "C:/Windows/Fonts/YuGothB.ttc"

INK = (18, 18, 20)
PAPER = (255, 255, 255)
ACCENT = (230, 30, 45)
SUB = (196, 196, 202)


def font(size):
    return ImageFont.truetype(FONT_PATH, size, index=0)


def wrap(draw, text, f, max_width):
    """日本語は単語境界が無いので、実測幅で1文字ずつ折り返す。"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        trial = cur + ch
        if draw.textlength(trial, font=f) > max_width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _draw_block(d, lines, f, cx, y, fill, line_gap, stroke=6):
    """縁取り付きで中央揃えに描く。ぼかし背景の上でも読めるようにする。"""
    for line in lines:
        w = d.textlength(line, font=f)
        d.text((cx - w / 2, y), line, font=f, fill=fill,
               stroke_width=stroke, stroke_fill=INK)
        y += f.size + line_gap
    return y


SCRIM_ALPHA = 168
SCRIM_FADE = 70          # 映像との境目をなじませる幅


def _scrim(img, top_zone, bottom_zone, width, height):
    """上下の死角を暗く覆う。

    ぼかし背景には元動画の焼き込み字幕がそのまま流れていて、読めないのに
    形だけ残るため雑音になる。暗く沈めると消え、文字の可読性も上がる。
    映像の帯には一切かけない。
    """
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, width, top_zone - SCRIM_FADE], fill=(0, 0, 0, SCRIM_ALPHA))
    d.rectangle([0, bottom_zone + SCRIM_FADE, width, height], fill=(0, 0, 0, SCRIM_ALPHA))
    # 境目は段階的に薄くして、帯の切り替わりを目立たせない
    for i in range(SCRIM_FADE):
        a = int(SCRIM_ALPHA * (1 - i / SCRIM_FADE))
        d.line([(0, top_zone - SCRIM_FADE + i), (width, top_zone - SCRIM_FADE + i)],
               fill=(0, 0, 0, a))
        d.line([(0, bottom_zone + SCRIM_FADE - i), (width, bottom_zone + SCRIM_FADE - i)],
               fill=(0, 0, 0, a))
    return Image.alpha_composite(img, layer)


def build(hook, footer, dest, width=1080, height=1920, handle="@com.-meibamen"):
    """上に hook、下に footer を置いた透過PNGを書き出す。

    映像は中央に width*9/16 の高さで乗るので、その上下が空く。
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    video_h = int(width * 9 / 16)
    top_zone = (height - video_h) // 2          # 映像の上端
    bottom_zone = top_zone + video_h            # 映像の下端

    if hook or footer:
        img = _scrim(img, top_zone, bottom_zone, width, height)
    d = ImageDraw.Draw(img)

    margin = 64
    max_w = width - margin * 2

    if handle and (hook or footer):
        f = font(34)
        w = d.textlength(handle, font=f)
        d.text((width / 2 - w / 2, 96), handle, font=f, fill=(150, 150, 158))

    if hook:
        f = font(78)
        lines = wrap(d, hook, f, max_w)
        block_h = len(lines) * f.size + (len(lines) - 1) * 18
        # 映像のすぐ上に接するように下詰めする。視線が映像へ流れる
        y = top_zone - block_h - 56
        d.rectangle([margin, y - 34, margin + 130, y - 22], fill=ACCENT)
        _draw_block(d, lines, f, width / 2, y, PAPER, 18)

    if footer:
        f = font(46)
        lines = wrap(d, footer, f, max_w)
        y = bottom_zone + 56
        _draw_block(d, lines, f, width / 2, y, SUB, 14, stroke=5)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest


def build_for_clip(video_id, clip, dest=None):
    dest = dest or (config.work_dir(video_id) / f"{clip['clip_id']}_overlay.png")
    return build(clip.get("hook"), clip.get("footer"), dest)
