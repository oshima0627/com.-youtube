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


# 行頭に来てはいけない文字（行頭禁則）。句読点・閉じ括弧・小書き仮名・長音符。
FORBID_LINE_START = "。、，．！？!?」』）］｝〉》ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮーゝゞ・:;"
# 行末に来てはいけない文字（行末禁則）。開き括弧。
FORBID_LINE_END = "「『（［｛〈《"

SENTENCE_END = "。！？!?"
COMMA = "、，,"
CLOSING = "」』）"
OPENING = "「『（"

# この語で終わる位置は文節の切れ目になりやすい。長いものから照合する。
# テ形の「て」を入れてある。無いと「たまらな／くなる」のように語中で割れた。
PARTICLES = ("という", "について", "によって", "からは", "までは", "ながら",
             "から", "まで", "より", "って", "ので", "けど", "ため", "たり",
             "では", "には", "とは", "でも", "ても",
             "は", "が", "を", "に", "へ", "と", "で", "も", "や", "の", "て")

MIN_LINE_RATIO = 0.45      # 1行の最短の目安。これを割る位置では折らない
ORPHAN_MAX = 2             # 最終行がこの文字数以下なら詰め直す


def _break_score(text, i):
    """text[:i] と text[i:] に割るときの良さ。大きいほど良く、0 は禁止。"""
    if i <= 0 or i >= len(text):
        return 0
    prev, nxt = text[i - 1], text[i]
    if nxt in FORBID_LINE_START:
        return 0
    if prev in FORBID_LINE_END:
        return 0
    if prev in SENTENCE_END:
        return 100
    if prev in COMMA:
        return 80
    if prev in CLOSING:
        return 60
    if nxt in OPENING:
        return 50
    for p in PARTICLES:
        if text[:i].endswith(p):
            return 20 + len(p)
    # 文字種が変わる位置（漢字↔かな、かな↔カタカナ など）は語の境目のことが多い。
    # 助詞が見つからないときの次善手。これが無いと、どこでも1点になった結果
    # 幅いっぱいの位置が選ばれ、語の途中で割れる
    if _script(prev) != _script(nxt):
        return 10
    return 1                # どこでも割れるが最後の手段


def _script(ch):
    """文字種をざっくり分類する。語の境目の推定に使う。"""
    o = ord(ch)
    if 0x3040 <= o <= 0x309F:
        return "hiragana"
    if 0x30A0 <= o <= 0x30FF:
        return "katakana"
    if 0x4E00 <= o <= 0x9FFF:
        return "kanji"
    if ch.isascii() and ch.isalnum():
        return "latin"
    return "other"


def _fits(draw, s, f, max_width):
    return draw.textlength(s, font=f) <= max_width


def _wrap_one(draw, text, f, max_width):
    """1文を折り返す。切れ目の良さを優先し、語の途中で割らない。"""
    lines, rest = [], text
    while rest:
        if _fits(draw, rest, f, max_width):
            lines.append(rest)
            break

        hi = 1
        while hi < len(rest) and _fits(draw, rest[:hi + 1], f, max_width):
            hi += 1
        lo = max(1, int(hi * MIN_LINE_RATIO))

        best_i, best_s = hi, -1
        for i in range(hi, lo - 1, -1):
            s = _break_score(rest, i)
            if s > best_s:
                best_s, best_i = s, i
            if best_s >= 60:            # 句読点・閉じ括弧なら十分good
                break
        lines.append(rest[:best_i])
        rest = rest[best_i:]
    return lines


def _split_sentences(text):
    """句点で区切る。**句点では必ず改行する**ため、文ごとに分けて折り返す。"""
    out, cur = [], ""
    for ch in text:
        cur += ch
        if ch in SENTENCE_END:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def wrap(draw, text, f, max_width):
    """日本語を読みやすい位置で折り返す。

    句点で改行し、やむを得ず折るときは文節の切れ目（読点・括弧・助詞のあと）を
    選ぶ。行頭に句読点や小書き仮名が来ないよう禁則処理もかける。
    最終行が1〜2文字だけ残る場合は、幅を詰めて割り直す。
    """
    if not text:
        return []
    lines = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        for sentence in _split_sentences(para):
            got = _wrap_one(draw, sentence, f, max_width)
            # 泣き別れ（最終行に1〜2文字だけ残る）を避ける
            if len(got) > 1 and len(got[-1]) <= ORPHAN_MAX:
                tighter = _wrap_one(draw, sentence, f, max_width * 0.88)
                if not (len(tighter) > 1 and len(tighter[-1]) <= ORPHAN_MAX):
                    got = tighter
            lines.extend(got)
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
