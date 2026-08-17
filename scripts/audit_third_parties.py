# -*- coding: utf-8 -*-
"""第三者の映り込みを目で確かめるための点検シートを作る。

    python scripts/audit_third_parties.py                  # 書き出し済み・投稿済みの全部
    python scripts/audit_third_parties.py <video_id> [clip_id ...]

**タイトルも概要欄も、画面に誰が映っているかを教えてくれない。** 実測で3回外した。

- fbKne9hTmgA: 体育館で大学のユニフォームを着た一般の方々
- MgO0lCUtlx4 auto01: 高校対中学のバスケの試合
- RGm5F2m12as: 外部の催眠術師。clip01/clip02 では画面の主役だった

いずれも screen.py / gate.py を通過している。許諾を依頼したのは BRDOCK だけで、
第三者の肖像はその射程外なので、**書き出したら必ずここでコマを見る。**

verify_hooks.py との違い: あちらは見出しの文言を焼き込みテロップと突き合わせる
ためのもので、区間の中央付近を4コマしか見ない。こちらは誰が映っているかを探す
ので、区間全体へ等間隔にコマを散らし、長い横型では枚数を増やす。
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image  # noqa: E402

from clipper import config, ledger, transcript  # noqa: E402

THUMB_W = 460
SHOTS_SHORT = 6
SECONDS_PER_SHOT = 60      # 横型はこの間隔で増やす
SHOTS_MAX = 12


def shots_for(length):
    if length <= 90:
        return SHOTS_SHORT
    return min(SHOTS_MAX, max(SHOTS_SHORT, int(length // SECONDS_PER_SHOT)))


def grab(src, at, dest):
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", str(at), "-i", str(src), "-frames:v", "1",
         "-vf", f"scale={THUMB_W}:-1", str(dest)],
        capture_output=True, encoding="utf-8", errors="replace")
    return dest if r.returncode == 0 and dest.exists() else None


def sheet_for(video_id, clip):
    wd = config.work_dir(video_id)
    src = wd / f"{clip['clip_id']}_src.mp4"
    if not src.exists():
        print(f"- {video_id}/{clip['clip_id']}: {src.name} が無いので飛ばす")
        return None

    length = clip["end"] - clip["start"]
    shots = shots_for(length)
    tiles = []
    for i in range(shots):
        at = length * (i + 0.5) / shots
        p = grab(src, at, wd / f"{clip['clip_id']}_audit_{i}.png")
        if p:
            tiles.append(Image.open(p))
    if not tiles:
        print(f"- {video_id}/{clip['clip_id']}: コマが抜けない")
        return None

    cols = 2 if len(tiles) <= 6 else 3
    rows = (len(tiles) + cols - 1) // cols
    w, h = tiles[0].size
    sheet = Image.new("RGB", (w * cols, h * rows), (16, 16, 16))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    dest = wd / f"{clip['clip_id']}_audit.png"
    sheet.save(dest)

    mark = "除外済" if clip.get("excluded") else ("投稿済" if clip.get("upload") else "在庫")
    print(f"[{clip['clip_id']}] {transcript.hms(clip['start'])}-"
          f"{transcript.hms(clip['end'])}  {len(tiles)}コマ  {mark}")
    if clip.get("excluded"):
        print(f"  除外理由: {clip['excluded']}")
    print(f"  確認: {dest}")
    return dest


def targets(argv):
    if argv:
        entry = ledger.load(argv[0])
        ids = set(argv[1:])
        clips = [c for c in entry["clips"] if not ids or c["clip_id"] in ids]
        return [(entry["video_id"], c) for c in clips]

    out = []
    for entry in ledger.all_entries():
        for c in entry["clips"]:
            if c.get("formats") or c.get("upload"):
                out.append((entry["video_id"], c))
    return out


def main():
    pairs = targets(sys.argv[1:])
    if not pairs:
        print("対象がありません")
        return 1
    made = 0
    for video_id, clip in pairs:
        print()
        if sheet_for(video_id, clip):
            made += 1
    print(f"\n{made}/{len(pairs)} 件のシートを作りました。"
          "メンバー以外が特定できる形で映っていたら config/exclusions.yaml に足す。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
