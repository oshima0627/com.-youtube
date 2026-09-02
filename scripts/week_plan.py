# -*- coding: utf-8 -*-
"""在庫から1週間分の投稿順を組んで、確認用の表を書き出す。

    python scripts/week_plan.py [開始日 YYYY-MM-DD] [1日の本数]

**予約は入れない。** ここが作るのは人が見るための表だけで、YouTube 側には
何も触れない。実際の予約は `clipper schedule --arm` で、許諾が granted に
なるまで gate が止める。

`clipper schedule --rebuild` を使わないのは、`config/schedule.yaml` の slots が
「2026-08-18 に Studio で実際に入っていた予約の写し」という記録だから。
組み直すと上書きされて消える。
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clipper import config, ledger  # noqa: E402

TIMES = ["07:00", "18:00", "12:00"]


def stock():
    """投稿できる状態の在庫を集める。除外されたものと横型は入れない。"""
    ex = set(config.exclusions().get("video_ids") or [])
    items = []
    for e in ledger.all_entries():
        if e["video_id"] in ex:
            continue
        for c in e["clips"]:
            if c.get("excluded") or "short" not in (c.get("formats") or []):
                continue
            up = c.get("upload") or {}
            # 公開済みは在庫ではない。台帳の privacy_status は
            # scripts/sync_privacy.py が実測に合わせている
            if c.get("published") or up.get("privacy_status") == "public":
                continue
            items.append({
                "video_id": e["video_id"], "clip_id": c["clip_id"],
                "youtube_video_id": up.get("youtube_video_id"),
                "state": "アップロード済（非公開）" if up else "書き出し済（未アップロード）",
                "title": c.get("planned_title") or up.get("title"),
                "new_format": "#shorts" in (c.get("planned_title") or ""),
                "duration": c.get("duration"),
            })
    return items


def interleave(items):
    """同じ元動画が続かないように散らす。"""
    from collections import defaultdict, deque
    buckets = defaultdict(deque)
    for it in items:
        buckets[it["video_id"]].append(it)
    out = []
    while any(buckets.values()):
        for vid in sorted(buckets, key=lambda v: -len(buckets[v])):
            if buckets[vid]:
                out.append(buckets[vid].popleft())
                break
    return out


def main():
    start = (date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1
             else date.today() + timedelta(days=1))
    per_day = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    items = interleave(stock())

    lines = [f"# 投稿計画（{start} から{per_day}本/日）", "",
             "**予約は入れていない。** この表は人が見るためのもので、"
             "YouTube 側には何も入っていない。", "",
             "| 枠 | 日時(JST) | 状態 | 元動画/クリップ | 尺 | タイトル |",
             "|---:|---|---|---|---:|---|"]
    n = 0
    for i, it in enumerate(items):
        day = start + timedelta(days=i // per_day)
        t = TIMES[i % per_day]
        mark = "" if it["new_format"] else " ※旧型式"
        lines.append(
            f"| {i+1} | {day} {t} | {it['state']}{mark} | "
            f"`{it['video_id']}/{it['clip_id']}` | {it['duration']}s | {it['title']} |")
        n += 1
    lines += ["", f"在庫 {n}本 = {n / per_day:.1f}日分。",
              "", "※旧型式 = メンバー名と `#shorts` が入っていないタイトル。"
              "`clipper retitle` で直す（API 復旧が要る）。"]
    dest = Path("docs/post-plan.md")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n-> {dest}")


if __name__ == "__main__":
    main()
