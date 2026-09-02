# -*- coding: utf-8 -*-
"""在庫から予約計画を組んで config/schedule.yaml に書く。**予約は入れない。**

    python scripts/build_schedule.py [開始日 YYYY-MM-DD] [1日の本数]

`clipper schedule --rebuild` を使わない理由が2つある。

1. `build_plan()` は**ショート1本/日**しか置かない。運用は2本/日
2. `config/schedule.yaml` の `slots` は「2026-08-18 に YouTube Studio で
   実際に入っていた予約の写し」という**記録**で、rebuild すると消える

ここでは記録を `archive` へ退避してから新しい `slots` を書く。
実際に予約を入れるのは `python -m clipper schedule --arm`。
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clipper import schedule  # noqa: E402
from week_plan import TIMES, interleave, stock  # noqa: E402


def main():
    start = (date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1
             else date.today() + timedelta(days=1))
    per_day = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    plan = schedule.load_plan()
    if plan.get("slots") and "archive" not in plan:
        plan["archive"] = {
            "note": "2026-08-18 に YouTube Studio で実際に入っていた予約の写し。"
                    "計画ではなく記録なので消さない",
            "slots": plan["slots"],
        }
        print(f"既存の slots {len(plan['slots'])}件を archive へ退避しました")

    items = interleave(stock())
    slots = []
    for i, it in enumerate(items):
        day = start + timedelta(days=i // per_day)
        slots.append({
            "video_id": it["video_id"], "clip_id": it["clip_id"],
            "youtube_video_id": it["youtube_video_id"],
            "title": it["title"],
            "publish_at_jst": f"{day:%Y-%m-%d} {TIMES[i % per_day]}",
        })
    plan["slots"] = slots
    plan["note"] = ("publish_at_jst は日本時間。arm するまで YouTube 側には何も入らない。"
                    "scripts/build_schedule.py が組んだもの")
    schedule.save_plan(plan)

    for s in slots:
        print(f"  {s['publish_at_jst']}  {s['video_id']}/{s['clip_id']}"
              f"  {s['youtube_video_id']}")
    print(f"\n{len(slots)}枠 = {len(slots) / per_day:.1f}日分 を書きました。"
          "**予約はまだ入っていません。**")
    print("入れるには: python -m clipper schedule --arm")


if __name__ == "__main__":
    main()
