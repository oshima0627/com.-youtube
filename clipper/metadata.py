# -*- coding: utf-8 -*-
"""投稿する動画のタイトル・概要欄・タグを組み立てる。

概要欄は決定論的に生成する。**元動画へのリンクと非提携の明示を人手に任せない。**
書き忘れが一度でも起きると、権利者から見たときの心証が最悪になる。

タイトルだけはクリップごとに人（セッション内のモデル）が書く。中身を見ないと
書けないため。ただし禁止表現の検査はここで機械的にかける。
"""

import re

from . import transcript

OFFICIAL_URL = "https://www.youtube.com/@comdot"

# 「公式」「公認」を名乗らない。権利者との関係が「黙認」である以上、
# 提携しているかのような表記は事実に反するうえ、なりすましとして扱われうる。
# tora-kirinuki では権利者ガイドラインが明文でこれを禁じていた。
BANNED_IN_TITLE = ("公式", "公認", "オフィシャル", "本人監修", "コラボ")

TITLE_MAX = 100
DESCRIPTION_MAX = 5000

TAGS = ["コムドット", "コムドット切り抜き", "切り抜き", "やまと", "ゆうた",
        "ゆうま", "ひゅうが", "あむぎり"]


class InvalidTitle(ValueError):
    pass


# ショートのタイトルの型。既存4チャンネルのショート120本を実測して決めた
# （scripts/market_scan.py）。伸びている上位は例外なくこの形だった。
#
#   赤組のマシュマロキャッチがダサくて最高すぎるwwwwww #コムドット #赤組
#   減量終わりにマックを食べるひゅうがが飯テロすぎた #コムドット #コムドット切り抜き
#
# 共通するのは3点。ハッシュタグを本文に入れる、メンバー名を入れる、
# 「〜すぎる」で断定して終わる。【】は長尺の作法でショートでは使われていない。
#
# **2026-09-02、この型が守られていなかったことが実測で分かった。**
# 公開済み13本のうちメンバー名を含むのは2本、`#shorts` は0本
# （競合は 22/27 と 46/120。docs/analytics-2026-09-02.md）。
# 型は docs に書いてあるだけで、`short_title()` はどこからも呼ばれておらず、
# タイトルは `--title` で素通しされていた。**以降は validate_title が機械的に弾く。**
SHORT_TAGS = ("#コムドット", "#コムドット切り抜き", "#shorts")

# タグにしてよい名前の名簿。自動字幕は固有名詞を崩すので
# （実例:「コニー母」→「スプリンガー母」）、推測した名前をタグにしない。
MEMBERS = ("やまと", "ゆうた", "ゆうま", "ひゅうが", "あむぎり")


def member_tags(members):
    """メンバー名をハッシュタグにする。名簿に無い名前は通さない。"""
    out = []
    for m in members or ():
        m = m.strip().lstrip("#")
        if not m:
            continue
        if m not in MEMBERS:
            raise InvalidTitle(
                f"メンバー名として認めていない『{m}』です。"
                f"使えるのは {'/'.join(MEMBERS)}")
        if f"#{m}" not in out:
            out.append(f"#{m}")
    return out


def short_title(body, members=(), extra_tags=""):
    """ショートのタイトルを組み立てる。本文＋ハッシュタグ。

    `members` は**映像で確認できたメンバーだけ**を渡す。字幕からの推測で
    渡さない。誰が映っているか分からないなら、確認してから呼ぶ。

    100文字に収まらないときは**末尾のタグから丸ごと落とす。**
    途中で切ると壊れたタグが残り、`#コムドット切り抜` のような別語になる。
    """
    body = (body or "").strip()
    if not body:
        raise InvalidTitle("タイトルの本文が空です")

    optional = member_tags(members) + [
        t if t.startswith("#") else f"#{t}"
        for t in (extra_tags or "").split() if t.strip()]
    base = list(SHORT_TAGS)

    fixed = " ".join([body] + base)
    if len(fixed) > TITLE_MAX:
        raise InvalidTitle(
            f"本文が長すぎます。基本タグ（{' '.join(base)}）を付けると "
            f"{len(fixed)}文字になり {TITLE_MAX} を超えます")

    tags = base + optional
    while len(" ".join([body] + tags)) > TITLE_MAX:
        tags.pop()                       # 末尾＝優先度の低いものから落とす
    # 組み立てたものを自分で検査する。API に投げる直前まで問題が残らないように
    return validate_title(" ".join([body] + tags), is_short=True)


def validate_title(title, is_short=False):
    """投稿前にタイトルを検査する。問題があれば InvalidTitle を投げる。"""
    if not title or not title.strip():
        raise InvalidTitle("タイトルが空です")
    if len(title) > TITLE_MAX:
        raise InvalidTitle(f"タイトルが {TITLE_MAX} 文字を超えています（{len(title)}）")
    for word in BANNED_IN_TITLE:
        if word in title:
            raise InvalidTitle(f"タイトルに使えない語『{word}』が含まれています")
    if "切り抜き" not in title:
        raise InvalidTitle("タイトルに『切り抜き』が必要です（切り抜きであることの明示）")
    if is_short:
        if "#shorts" not in title.lower():
            raise InvalidTitle(
                "ショートのタイトルに『#shorts』が必要です。"
                "short_title() で組み立ててください")
        if not any(m in title for m in MEMBERS):
            raise InvalidTitle(
                "ショートのタイトルにメンバー名が必要です"
                f"（{'/'.join(MEMBERS)}）。本文で名指しするか #名前 を足してください。"
                "**映像で確認できたメンバーだけ**を書くこと")
    return title


def source_url(video_id, at=None):
    base = f"https://www.youtube.com/watch?v={video_id}"
    return f"{base}&t={int(at)}s" if at else base


def build_description(entry, clip, is_short=True):
    """概要欄を組み立てる。元動画リンクと非提携の明示を必ず含める。"""
    vid = entry["video_id"]
    meta = entry.get("meta") or {}
    lines = [
        "▼この場面の元動画（コムドット公式チャンネル）",
        meta.get("title") or "",
        source_url(vid, clip["start"]),
        "",
        "コムドットさんの動画から名場面を切り抜いてお届けしています。",
        "このチャンネルは有志による切り抜きチャンネルで、コムドットさん本人および",
        "所属事務所とは関係がありません。",
        "",
        "▼コムドット公式チャンネル",
        OFFICIAL_URL,
        "",
        "権利者様からの削除・修正のご要望には速やかに対応いたします。",
    ]
    if is_short:
        lines += ["", "#コムドット #切り抜き #Shorts"]
    return "\n".join(lines)[:DESCRIPTION_MAX]


def suggest_title_context(entry, clip, segments):
    """タイトルを書くための材料を返す。区間の発言と長さ。

    タイトル自体は自動生成しない。自動字幕は固有名詞と数値が崩れるため、
    引用をそのまま使うと誤った台詞を人物に帰属させることになる。
    """
    spoken = [s["text"] for s in transcript.slice_segments(
        segments, clip["start"], clip["end"])]
    return {
        "video_title": (entry.get("meta") or {}).get("title"),
        "range": f"{transcript.hms(clip['start'])}-{transcript.hms(clip['end'])}",
        "duration": round(clip["end"] - clip["start"], 1),
        "transcript": " ".join(spoken),
    }


def build_body(entry, clip, title, is_short=True):
    """videos.insert に渡す snippet/status を作る。privacy は呼び出し側が決める。"""
    validate_title(title, is_short=is_short)
    return {
        "title": title,
        "description": build_description(entry, clip, is_short),
        "tags": TAGS,
        "categoryId": "24",             # Entertainment
        # 言語は必ず明示する。省略すると YouTube が推測して英語判定されることがある
        "defaultLanguage": "ja",
        "defaultAudioLanguage": "ja",
    }
