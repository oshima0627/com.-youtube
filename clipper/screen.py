# -*- coding: utf-8 -*-
"""素材として使ってよい動画かを決定論的に判定する。

gate の前段。ここを通らなかった動画は文字起こしにも進ませない。
判定は全て機械的な文字列一致で、LLM を通さない。
"""

from . import config, fetch


def screen(video_id):
    """{ok, reasons, meta} を返す。ok=False なら素材にしない。"""
    reasons = []

    try:
        meta = fetch.fetch_meta(video_id)
    except fetch.NotClippable as e:
        return {"video_id": video_id, "ok": False, "reasons": [str(e)], "meta": None}

    ex = config.exclusions()
    title = meta.get("title") or ""
    description = meta.get("description") or ""

    if video_id in (ex.get("video_ids") or []):
        reasons.append("exclusions.yaml の video_ids に登録されている")

    for pat in ex.get("title_patterns") or []:
        if pat in title:
            reasons.append(f"タイトルに除外語『{pat}』を含む")

    for pat in ex.get("description_patterns") or []:
        if pat in description:
            reasons.append(f"概要欄に除外語『{pat}』を含む")

    return {"video_id": video_id, "ok": not reasons, "reasons": reasons, "meta": meta}
