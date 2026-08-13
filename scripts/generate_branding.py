# -*- coding: utf-8 -*-
"""チャンネルのアイコン / バナーを生成する。

YouTube の入稿仕様:
  アイコン : 800x800 px (表示は円形クロップ)
  バナー   : 2048x1152 px / 全デバイス共通の可視領域は中央 1235x338 px
             PC は中央 2048x423 px、TV は全面が表示される

意匠の方針:
  既存のコムドット切り抜きチャンネル（コムの巣窟 9.96万人、コムドットの元
  食わず嫌い 1.64万人ほか）を実見した結果、このジャンルの共通言語は
  「白背景 / チャンネル名を袋文字で中央に大きく / 赤系アクセント /
   下部に赤で切り抜き表記」だった。その型を踏襲する。
  ただしメンバーの写真・似顔絵は著作権と肖像権の対象なので使わず、
  同じ密度を集中線で出す。

名称を変えるときは下の CHANNEL_* / BANNER_* を書き換えて再実行するだけでよい。
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ---- チャンネル定義 ----------------------------------------------------
ICON_HEAD = "コムドットの"      # アイコン上段
ICON_KEY = "名場面"             # アイコン主役
ICON_FOOT = "切り抜きch"        # アイコン下段

BANNER_KICKER = "ファンによる切り抜きまとめ"  # 「非公式」は概要欄が担当する
BANNER_TITLE = "コムドット名場面ch"
BANNER_BADGE = "切り抜き"
BANNER_TAGLINE = "“あの瞬間”だけを、まとめて。"
HANDLE = "@com.-meibamen"

# ---- 配色 --------------------------------------------------------------
RED = (230, 30, 45)
INK = (22, 22, 26)
PAPER = (255, 255, 255)
BURST = (255, 231, 233)
WHITE = (245, 245, 245)
GRAY = (150, 150, 158)

FONT_PATH = "C:/Windows/Fonts/YuGothB.ttc"

OUT = Path(__file__).resolve().parent.parent / "assets" / "branding"


def font(size):
    return ImageFont.truetype(FONT_PATH, size, index=0)


def draw_centered(d, cx, cy, text, f, fill, stroke=0, stroke_fill=None):
    """テキストの実インクボックスの中心を (cx, cy) に合わせる。"""
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text((cx - (l + r) / 2, cy - (t + b) / 2), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill)


def draw_left(d, x, cy, text, f, fill):
    """左端 x・縦中心 cy にテキストを置き、実インク幅を返す。"""
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text((x - l, cy - (t + b) / 2), text, font=f, fill=fill)
    return r - l


def text_width(d, text, f):
    l, _, r, _ = d.textbbox((0, 0), text, font=f)
    return r - l


def dashed_line(d, x0, x1, y, fill, width, on=26, off=18):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + on, x1), y)], fill=fill, width=width)
        x += on + off


def scissors(d, cx, cy, fill, scale=1.0):
    """切り抜きを示すハサミ。円 2 つ + 交差する刃 2 本で構成する。"""
    s = scale
    r = 17 * s
    d.ellipse([cx - r, cy - 38 * s - r, cx + r, cy - 38 * s + r], outline=fill, width=int(8 * s))
    d.ellipse([cx - r, cy + 38 * s - r, cx + r, cy + 38 * s + r], outline=fill, width=int(8 * s))
    d.line([(cx + 14 * s, cy - 30 * s), (cx + 86 * s, cy + 22 * s)], fill=fill, width=int(9 * s))
    d.line([(cx + 14 * s, cy + 30 * s), (cx + 86 * s, cy - 22 * s)], fill=fill, width=int(9 * s))


def halftone(d, w, h, fill, pitch=44, r=7):
    """ハーフトーンのドット。メンバー写真を使えない分の密度をここで補う。
    放射状の集中線は赤白だと旭日模様に読めてしまうため採らない。"""
    for row, y in enumerate(range(0, h + pitch, pitch)):
        offset = (pitch // 2) if row % 2 else 0
        for x in range(-pitch, w + pitch, pitch):
            d.ellipse([x + offset - r, y - r, x + offset + r, y + r], fill=fill)


# ---- アイコン ----------------------------------------------------------
def build_icon():
    """円形クロップ前提。既存切り抜きチャンネルの型に合わせ、
    白地・中央に袋文字・下部に赤の切り抜き表記で構成する。"""
    size = 800
    img = Image.new("RGB", (size, size), PAPER)
    d = ImageDraw.Draw(img)

    halftone(d, size, size, BURST)

    # 縁の赤いリング。ライトテーマの白背景に溶けないようにする
    d.ellipse([14, 14, size - 14, size - 14], outline=RED, width=24)

    draw_centered(d, size / 2, 186, ICON_HEAD, font(70), INK)

    # 主役。白 → 黒 → 赤の順に重ねて二重の袋文字にする
    f_key = font(206)
    for stroke, color in ((30, PAPER), (16, INK), (0, RED)):
        draw_centered(d, size / 2, 402, ICON_KEY, f_key, color,
                      stroke=stroke, stroke_fill=color)

    # 下段の赤ピル。円の縁に触れさせず、白い輪郭を全周に残す
    f_foot = font(56)
    fw = text_width(d, ICON_FOOT, f_foot)
    pill_w = fw + 108
    d.rounded_rectangle([size / 2 - pill_w / 2, 596, size / 2 + pill_w / 2, 700],
                        radius=52, fill=RED)
    scissors(d, size / 2 - pill_w / 2 + 42, 648, PAPER, scale=0.42)
    draw_centered(d, size / 2 + 22, 648, ICON_FOOT, f_foot, PAPER)

    img.save(OUT / "icon_800.png")
    return img


# ---- バナー ------------------------------------------------------------
def build_banner():
    W, H = 2048, 1152
    img = Image.new("RGB", (W, H), INK)

    # 全面に薄い斜線。TV 表示でも間が持つようにする
    stripes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stripes)
    for x in range(-H, W + H, 64):
        sd.line([(x, 0), (x + H, H)], fill=(230, 30, 45, 18), width=26)
    img = Image.alpha_composite(img.convert("RGBA"), stripes).convert("RGB")
    d = ImageDraw.Draw(img)

    # 全デバイス共通の可視領域
    sx, sy = (W - 1235) // 2, (H - 338) // 2

    # PC 表示（中央 2048x423）でだけ見える右側の余白を切り抜きモチーフで埋める。
    # スマホ可視領域（x <= 1641）には掛からない位置に置く
    scissors(d, 1726, H // 2 - 30, (62, 40, 44), scale=2.4)
    dashed_line(d, 1950, 2030, H // 2 - 30, (62, 40, 44), width=15, on=40, off=28)

    # 左端のアクセントバー
    d.rectangle([sx, sy + 26, sx + 12, sy + 312], fill=RED)

    tx = sx + 56
    draw_left(d, tx, sy + 52, BANNER_KICKER, font(36), (255, 120, 128))
    draw_left(d, tx, sy + 150, BANNER_TITLE, font(116), WHITE)

    # 【切り抜き】はバッジとして敷く
    f_badge = font(44)
    bw = text_width(d, BANNER_BADGE, f_badge)
    by = sy + 256
    d.rounded_rectangle([tx, by - 40, tx + bw + 52, by + 40], radius=10, fill=RED)
    draw_left(d, tx + 26, by, BANNER_BADGE, f_badge, PAPER)

    draw_left(d, tx + bw + 84, by, BANNER_TAGLINE, font(40), GRAY)

    img.save(OUT / "banner_2048x1152.png")
    return img


# ---- 確認用シート ------------------------------------------------------
def build_preview(icon, banner):
    W, H = 1500, 1080
    img = Image.new("RGB", (W, H), (26, 26, 30))
    d = ImageDraw.Draw(img)
    f_cap = font(24)

    y = 34
    d.text((40, y), "バナー / PC表示 (中央 2048x423 を切り出し)", font=f_cap, fill=GRAY)
    pc = banner.crop((0, (1152 - 423) // 2, 2048, (1152 + 423) // 2)).resize((1420, 293))
    img.paste(pc, (40, y + 38))

    y = 400
    d.text((40, y), "バナー / スマホ表示 (中央 1235x338 を切り出し)", font=f_cap, fill=GRAY)
    mb = banner.crop(((2048 - 1235) // 2, (1152 - 338) // 2,
                      (2048 + 1235) // 2, (1152 + 338) // 2)).resize((880, 241))
    img.paste(mb, (40, y + 38))

    d.text((960, y), "アイコン / 実表示サイズ", font=f_cap, fill=GRAY)
    mask = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 799, 799], fill=255)
    x = 960
    for px in (128, 88, 48, 24):
        ic = icon.resize((px, px))
        mk = mask.resize((px, px))
        img.paste(ic, (x, y + 60), mk)
        d.text((x, y + 60 + px + 8), f"{px}px", font=font(18), fill=GRAY)
        x += px + 26

    # 登録チャンネル欄の再現。ダーク / ライト両テーマで円が欠けないか確認する
    y = 720
    d.text((40, y), "登録チャンネル欄での見え方 / ダークテーマ", font=f_cap, fill=GRAY)
    d.text((770, y), "同 / ライトテーマ", font=f_cap, fill=GRAY)
    d.rectangle([756, y + 34, W - 40, H - 30], fill=(255, 255, 255))

    for i, px in enumerate((88, 48)):
        row = y + 60 + i * 112
        ic = icon.resize((px, px))
        mk = mask.resize((px, px))
        for x0, fg, sub in ((48, WHITE, GRAY), (784, (15, 15, 15), (110, 110, 116))):
            img.paste(ic, (x0, row), mk)
            d.text((x0 + px + 20, row + px / 2 - 20), BANNER_TITLE, font=font(30), fill=fg)
            d.text((x0 + px + 20, row + px / 2 + 14), HANDLE, font=font(22), fill=sub)

    img.save(OUT / "preview.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    banner = build_banner()
    build_preview(icon, banner)
    for p in sorted(OUT.glob("*.png")):
        with Image.open(p) as im:
            print(f"{p.name}: {im.size[0]}x{im.size[1]} / {p.stat().st_size / 1024:.0f} KB")
