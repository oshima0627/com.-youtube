# -*- coding: utf-8 -*-
"""文字起こしの整形。

extract ステージ（セッション内で人／モデルが読んで候補を出す工程）が扱いやすい
形に落とす。自動字幕は 1〜2 秒ごとに切れていて長文として読めないため、
一定の時間幅にまとめ直す。
"""

import json

from . import config


def condense(segments, window=60):
    """window 秒ごとにまとめ、[{start, end, text}] を返す。"""
    if not segments:
        return []

    blocks = []
    bucket, bucket_start = [], segments[0]["start"]
    for s in segments:
        if s["start"] - bucket_start >= window and bucket:
            blocks.append({
                "start": round(bucket_start, 1),
                "end": round(bucket[-1]["end"], 1),
                "text": "".join(bucket_texts(bucket)),
            })
            bucket, bucket_start = [], s["start"]
        bucket.append(s)

    if bucket:
        blocks.append({
            "start": round(bucket_start, 1),
            "end": round(bucket[-1]["end"], 1),
            "text": "".join(bucket_texts(bucket)),
        })
    return blocks


def bucket_texts(bucket):
    """自動字幕は前後のセグメントで語句が重複することがあるため、
    直前と同一のテキストは落とす。"""
    prev = None
    for s in bucket:
        if s["text"] != prev:
            yield s["text"]
        prev = s["text"]


def hms(seconds):
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def write_digest(video_id, segments, window=60):
    """人が読める形のダイジェストを work/<id>/digest.md に書き出す。"""
    blocks = condense(segments, window)
    lines = [f"# {video_id} 文字起こしダイジェスト（{window}秒ごと）", ""]
    for b in blocks:
        lines.append(f"## [{hms(b['start'])} - {hms(b['end'])}]")
        lines.append(b["text"])
        lines.append("")

    path = config.work_dir(video_id) / "digest.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def slice_segments(segments, start, end):
    """指定区間に重なるセグメントだけを返す。字幕焼き込みに使う。"""
    return [s for s in segments if s["end"] > start and s["start"] < end]
