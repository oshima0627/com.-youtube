# -*- coding: utf-8 -*-
"""投稿してよいかを機械的に判定する。

無人運転で効くのは「人が見ていれば気づくこと」を機械が代わりに止められるか
どうか。ここは**決定論的な判定だけ**を置く。LLM は通さない。判断が要るもの
（面白いか）は extract 側の仕事で、ここは絶対に破らせない条件だけを見る。

判定に落ちたものは捨てずに held にして理由を残す。理由が残っていれば、
条件のほうが厳しすぎたのか素材が悪かったのかを後から切り分けられる。
"""

import json
from datetime import date

from . import config, transcript

RUNTIME_PATH = config.ROOT / "state" / "runtime.json"

DEFAULT_RUNTIME = {
    "kill_switch": False,
    "kill_reason": None,
    "published": {},          # {"YYYY-MM-DD": ["video_id/clip_id", ...]}
}


def load_runtime():
    if not RUNTIME_PATH.exists():
        return dict(DEFAULT_RUNTIME)
    return {**DEFAULT_RUNTIME, **json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))}


def save_runtime(rt):
    RUNTIME_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_PATH.write_text(json.dumps(rt, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    return rt


def trip_kill_switch(reason):
    """異常を検知したら全停止する。解除は手動のみ。

    自動で復帰させない。異常を検知したのに自動で再開する仕組みは
    安全装置として意味を持たない。
    """
    rt = load_runtime()
    rt["kill_switch"] = True
    rt["kill_reason"] = reason
    return save_runtime(rt)


def _published_ids(rt):
    return {i for ids in rt["published"].values() for i in ids}


def evaluate(entry, clip, segments=None, today=None, runtime=None):
    """1つのクリップについて {result, reasons} を返す。

    条件は上から順に見て、外れたものを全部集める。1つ目で打ち切らないのは、
    保留の理由が複数あるときに1つずつ潰す羽目になるのを避けるため。
    """
    reasons = []
    rt = runtime if runtime is not None else load_runtime()
    today = today or date.today().isoformat()

    # 1. 許諾。既定が pending なので、回答が来るまで1本も出ない
    perm = config.permission()
    if perm.get("status") != "granted":
        reasons.append(f"許諾ステータスが {perm.get('status')}（granted ではない）")

    # 1-2. 収益化の許諾条件。**収益化しているときだけ**見る。
    #      止めたいのは「許諾の範囲を超えて収益を得ること」であって投稿そのもの
    #      ではないので、収益化していないうちは unknown でも通す。収益化した
    #      日に自動で効き始める安全装置として置く。
    cond = perm.get("conditions") or {}
    monetized = (config.settings().get("channel") or {}).get("monetization_enabled")
    if monetized and cond.get("monetization") != "allowed":
        reasons.append(
            f"チャンネルが収益化されているが、許諾の収益化条件が "
            f"{cond.get('monetization')}（allowed ではない）")

    # 2. 除外リストに載っている動画
    ex = config.exclusions()
    if entry["video_id"] in (ex.get("video_ids") or []):
        reasons.append("exclusions.yaml の video_ids に登録されている")

    # 3-4. タイトル・概要欄の除外語（screen と同じ条件をここでも見る。
    #      screen を通さずに台帳へ入った動画を素通りさせないため）
    meta = entry.get("meta") or {}
    for pat in ex.get("title_patterns") or []:
        if pat in (meta.get("title") or ""):
            reasons.append(f"タイトルに除外語『{pat}』を含む")
    for pat in ex.get("description_patterns") or []:
        if pat in (meta.get("description") or ""):
            reasons.append(f"概要欄に除外語『{pat}』を含む")

    # 5. クリップ区間の発言に禁止語が入っていないか
    if segments:
        spoken = "".join(s["text"] for s in transcript.slice_segments(
            segments, clip["start"], clip["end"]))
        for term in ex.get("blocked_terms") or []:
            if term and term in spoken:
                reasons.append(f"発言に禁止語『{term}』を含む")

    # 6. 同じクリップを既に出していないか
    key = f"{entry['video_id']}/{clip['clip_id']}"
    if key in _published_ids(rt):
        reasons.append("同じクリップを既に投稿している")

    # 7. 当日の投稿本数の上限。暴走時の被害を本数で頭打ちにする
    limit = config.settings()["limits"]["max_publish_per_day"]
    if len(rt["published"].get(today, [])) >= limit:
        reasons.append(f"本日の投稿上限 {limit} 本に達している")

    # 8. キルスイッチ
    if rt.get("kill_switch"):
        reasons.append(f"キルスイッチが立っている: {rt.get('kill_reason')}")

    return {"result": "held" if reasons else "pass", "reasons": reasons}


def record_published(entry, clip, today=None):
    """投稿できたものを記録する。上限と重複の判定はこの記録を見る。"""
    rt = load_runtime()
    today = today or date.today().isoformat()
    rt["published"].setdefault(today, []).append(
        f"{entry['video_id']}/{clip['clip_id']}")
    return save_runtime(rt)
