# -*- coding: utf-8 -*-
"""使える素材の候補プールを作る。

    python scripts/build_source_pool.py [本数]

素材の歩留まりが低い。2026-08-14 時点で、直近12本は全て除外対象だった
（イベント回・コラボ回・メンバー限定・災害への言及）。過去回を掘る必要がある。

**2段構えにする。** タイトルの判定は一覧取得だけで済んで安いが、概要欄の判定は
1本ずつ取りに行くので高い。先にタイトルで落としてから、通ったものだけ取りに行く。

なお**この判定を通っても使えるとは限らない。** 画面に誰が映っているかは
タイトルにも概要欄にも出ない。実際に体育館で大学のユニフォームを着た一般の方が
映り込んでいた回が通過した。採用前に必ず scripts/verify_hooks.py で映像を見る。
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clipper import config, ledger, screen, transcript  # noqa: E402

CHANNEL = "https://www.youtube.com/@comdot/videos"

# タイトルだけで落とせるもの。英語タイトルはメンバーシップ限定か翻訳版が多く、
# 実測でも軒並みメンバー限定だった
CHEAP_REJECT = ("CDF", "コラボ", "生配信", "Official Music Video", "Teaser")


def listing(limit):
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node",
         "--flat-playlist", "--playlist-end", str(limit), "--dump-json", CHANNEL],
        capture_output=True, encoding="utf-8", errors="replace")
    out = []
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        out.append({"id": d.get("id"), "title": d.get("title") or "",
                    "duration": d.get("duration") or 0})
    return out


def cheap_pass(v):
    """一覧の情報だけで判定できるもの。"""
    if any(w in v["title"] for w in CHEAP_REJECT):
        return False, "タイトルで除外"
    # 日本語の【】タイトルが本編。英語タイトルはメンバー限定か翻訳版が多い
    if "【" not in v["title"]:
        return False, "本編の型（【】）でない"
    if v["duration"] and v["duration"] < 900:
        return False, "15分未満（本編ではない可能性）"
    return True, None


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    vids = listing(limit)
    print(f"一覧 {len(vids)}本")

    known = {e["video_id"] for e in ledger.all_entries()}
    lines = ["# 素材候補プール", "",
             "| 判定 | id | 尺 | タイトル | 理由 |", "|---|---|---:|---|---|"]
    pool = []

    for v in vids:
        if v["id"] in known:
            lines.append(f"| 済 | {v['id']} | {v['duration']}s | "
                         f"{v['title'][:40]} | 台帳にあり |")
            continue
        ok, why = cheap_pass(v)
        if not ok:
            lines.append(f"| × | {v['id']} | {v['duration']}s | "
                         f"{v['title'][:40]} | {why} |")
            continue
        # ここで初めて概要欄を取りに行く
        r = screen.screen(v["id"])
        if r["ok"]:
            pool.append(v)
            lines.append(f"| ○ | {v['id']} | {v['duration']}s | "
                         f"{v['title'][:40]} | |")
        else:
            lines.append(f"| × | {v['id']} | {v['duration']}s | "
                         f"{v['title'][:40]} | {r['reasons'][0][:30]} |")
        print(f"  {'○' if r['ok'] else '×'} {v['id']} {v['title'][:34]}")

    lines += ["", f"## 通過 {len(pool)}本", "",
              "**この判定を通っても使えるとは限らない。**",
              "画面に誰が映っているかはタイトルにも概要欄にも出ない。",
              "採用前に scripts/verify_hooks.py で映像を見ること。", ""]
    for v in pool:
        lines.append(f"- `{v['id']}` {transcript.hms(v['duration'])} {v['title']}")

    dest = config.ROOT / "work" / "source_pool.md"
    dest.parent.mkdir(parents=True, exist_ok=True)   # worktree には work/ が無い
    dest.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n通過 {len(pool)}本 → {dest}")


if __name__ == "__main__":
    main()
