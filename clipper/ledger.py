# -*- coding: utf-8 -*-
"""動画ごとの台帳。data/videos/<video_id>.json に状態と候補を持つ。

台帳だけを git で追跡する。何をいつ投稿したか、何を保留にしてなぜかが
コミット履歴に残り、権利者からの問い合わせに対して提示できる記録になる。
"""

import json

from . import config

# 状態は一方向に進む。各ステージは自分の入力状態のものだけを処理する。
STATES = [
    "discovered",
    "fetched",
    "transcribed",
    "extracted",
    "gated",
    "rendered",
    "published",
]


def path(video_id):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return config.DATA_DIR / f"{video_id}.json"


def load(video_id):
    p = path(video_id)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(entry):
    with open(path(entry["video_id"]), "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return entry


def create(video_id, meta):
    """新規エントリ。既にあれば既存を返し、上書きしない（冪等）。"""
    existing = load(video_id)
    if existing:
        return existing
    return save({
        "video_id": video_id,
        "state": "discovered",
        "meta": meta,
        "clips": [],
        "notes": [],
    })


def set_state(entry, state):
    if state not in STATES:
        raise ValueError(f"未知の状態: {state}")
    entry["state"] = state
    return save(entry)


def add_note(entry, note):
    entry["notes"].append(note)
    return save(entry)


def put_clips(entry, clips):
    """抽出した候補で置き換える。clip_id で冪等に上書きする。"""
    by_id = {c["clip_id"]: c for c in entry["clips"]}
    for c in clips:
        by_id[c["clip_id"]] = {**by_id.get(c["clip_id"], {}), **c}
    entry["clips"] = sorted(by_id.values(), key=lambda c: c["start"])
    return save(entry)


def all_entries():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(config.DATA_DIR.glob("*.json")):
        with open(p, encoding="utf-8") as f:
            yield json.load(f)
