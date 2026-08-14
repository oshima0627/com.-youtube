# -*- coding: utf-8 -*-
"""既存のコムドット切り抜きチャンネルを実測して、何が伸びているかを見る。

    python scripts/market_scan.py

**何を作るかの判断材料を取るための道具。** 磨き方ではなく、題材の選び方に効く。
tora-kirinuki は技術的に完成したパイプラインで8本公開して総再生4回だった。
作り込みだけでは伸びない。伸びている在庫の中身を見るほうが先。

チャンネルは登録者順。数字は実行時点のもの。
"""

import json
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHANNELS = [
    ("コムの巣窟", "https://www.youtube.com/@com.soukutu10.1"),
    ("モモンガ", "https://www.youtube.com/@_0w0__comdot"),
    ("コムピース", "https://www.youtube.com/@compeace91"),
    ("元食わず嫌い", "https://www.youtube.com/@com.no_krnk_ch"),
]

LIMIT = 60          # 1チャンネルあたり何本見るか


def fetch(url, limit=LIMIT):
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node",
         "--flat-playlist", "--playlist-end", str(limit),
         "--dump-json", f"{url}/videos"],
        capture_output=True, encoding="utf-8", errors="replace")
    out = []
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        out.append({
            "id": d.get("id"),
            "title": d.get("title") or "",
            "views": d.get("view_count") or 0,
            "duration": d.get("duration") or 0,
        })
    return out


def main():
    all_rows = []
    lines = ["# コムドット切り抜きの実測", ""]

    for name, url in CHANNELS:
        vids = fetch(url)
        if not vids:
            lines.append(f"## {name}: 取得できず")
            continue
        for v in vids:
            v["channel"] = name
        all_rows += vids

        views = [v["views"] for v in vids if v["views"]]
        durs = [v["duration"] for v in vids if v["duration"]]
        lines.append(f"## {name}  {len(vids)}本")
        if views:
            lines.append(f"- 再生数 中央値 {int(statistics.median(views)):,} / "
                         f"最大 {max(views):,}")
        if durs:
            shorts = [d for d in durs if d <= 90]
            lines.append(f"- 尺 中央値 {int(statistics.median(durs))}秒 / "
                         f"90秒以下が {len(shorts)}/{len(durs)}本")
        lines.append("")

    lines.append("## 全チャンネル 再生数 上位20")
    lines.append("")
    lines.append("| 再生数 | 尺 | チャンネル | タイトル |")
    lines.append("|---:|---:|---|---|")
    for v in sorted(all_rows, key=lambda x: -x["views"])[:20]:
        lines.append(f"| {v['views']:,} | {v['duration']}s | {v['channel']} | "
                     f"{v['title'][:52]} |")

    lines.append("")
    lines.append("## 下位10（伸びていないもの）")
    lines.append("")
    lines.append("| 再生数 | 尺 | チャンネル | タイトル |")
    lines.append("|---:|---:|---|---|")
    for v in sorted(all_rows, key=lambda x: x["views"])[:10]:
        lines.append(f"| {v['views']:,} | {v['duration']}s | {v['channel']} | "
                     f"{v['title'][:52]} |")

    dest = Path(__file__).resolve().parents[1] / "work" / "market_scan.md"
    dest.write_text("\n".join(lines), encoding="utf-8")
    print(f"{dest}  ({len(all_rows)}本)")


if __name__ == "__main__":
    main()
