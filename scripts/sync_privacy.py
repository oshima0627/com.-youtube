# -*- coding: utf-8 -*-
"""台帳の privacy_status を、公開側で実測した状態に合わせる。

    python scripts/sync_privacy.py

**台帳は20本すべて private と記録していたが、実際は14本が公開済みだった。**
このずれを残したまま schedule や一括操作をすると、公開済みのものを
もう一度予約枠に入れてしまう。

判定は yt-dlp の公開値で行う。認証は要らない。
`availability=public` なら public、取得できず "Private video" なら private。
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clipper import ledger  # noqa: E402


def probe(yt_id):
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--no-warnings", "-J",
         f"https://www.youtube.com/watch?v={yt_id}"],
        capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return "private" if "Private video" in (r.stderr or "") else None
    try:
        return json.loads(r.stdout).get("availability")
    except json.JSONDecodeError:
        return None


def main():
    changed = 0
    for entry in ledger.all_entries():
        touched = []
        for c in entry["clips"]:
            up = c.get("upload")
            if not up or not up.get("youtube_video_id"):
                continue
            actual = probe(up["youtube_video_id"])
            if actual is None:
                print(f"? {up['youtube_video_id']} 判定できず（据え置き）")
                continue
            if up.get("privacy_status") != actual:
                print(f"~ {up['youtube_video_id']} "
                      f"{up.get('privacy_status')} -> {actual}")
                up["privacy_status"] = actual
                touched.append(c)
                changed += 1
            if actual == "public":
                c["published"] = True
        if touched:
            ledger.put_clips(entry, touched)
    print(f"{changed}件を直しました（実測は yt-dlp の公開値）")


if __name__ == "__main__":
    main()
