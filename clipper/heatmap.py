# -*- coding: utf-8 -*-
"""YouTube の「最も再生された部分」を取得して候補区間の根拠にする。

視聴者が実際に繰り返し見た箇所という観測データであり、文字起こしから
面白さを推測するより確度が高い。extract ステージはまずこれを使い、
文字起こしは「その区間で何が起きているか」の説明に回す。
"""

import json
import subprocess
import sys
from pathlib import Path

from . import config, fetch


def fetch_heatmap(video_id):
    """[{start, end, value}] を返す。データが無い動画では None。"""
    cached = config.work_dir(video_id) / "heatmap.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node",
         "--dump-single-json", "--skip-download", fetch.url(video_id)],
        capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-1500:])

    raw = json.loads(r.stdout).get("heatmap")
    if not raw:
        return None

    points = [{"start": p["start_time"], "end": p["end_time"], "value": p["value"]}
              for p in raw]
    cached.write_text(json.dumps(points, ensure_ascii=False), encoding="utf-8")
    return points


def peaks(points, count=5, min_gap=120.0):
    """値の高い順に、互いに min_gap 秒以上離れた山を count 個返す。

    隣接する高得点が同じ場面を指すため、近すぎるものは 1 つにまとめる。
    """
    ranked = sorted(points, key=lambda p: p["value"], reverse=True)
    chosen = []
    for p in ranked:
        center = (p["start"] + p["end"]) / 2
        if all(abs(center - (c["start"] + c["end"]) / 2) >= min_gap for c in chosen):
            chosen.append(p)
        if len(chosen) >= count:
            break
    return sorted(chosen, key=lambda p: p["start"])


def value_at(points, seconds):
    """指定時刻のヒート値。選んだ区間の妥当性を後から検証するのに使う。"""
    for p in points:
        if p["start"] <= seconds < p["end"]:
            return p["value"]
    return None


def rank_of(points, seconds):
    """指定時刻が全区間中で何番目に高いか（1 が最高）。"""
    v = value_at(points, seconds)
    if v is None:
        return None
    return sum(1 for p in points if p["value"] > v) + 1
