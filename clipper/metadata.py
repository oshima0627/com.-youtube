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


def validate_title(title):
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
    validate_title(title)
    return {
        "title": title,
        "description": build_description(entry, clip, is_short),
        "tags": TAGS,
        "categoryId": "24",             # Entertainment
        # 言語は必ず明示する。省略すると YouTube が推測して英語判定されることがある
        "defaultLanguage": "ja",
        "defaultAudioLanguage": "ja",
    }
