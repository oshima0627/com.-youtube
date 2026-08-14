# -*- coding: utf-8 -*-
"""見出しと補足を、元動画の焼き込みテロップと突き合わせるための確認シートを作る。

    python scripts/verify_hooks.py <video_id> [<clip_id> ...]

自動字幕は固有名詞が崩れる。実例として ASR が「音を立てたら即あり極白の食事」と
出したので「即アウト」と書いたが、映像のカードは「音を立てたら即ハリセン
極悪の食事」だった。**ルールを事実と違う形で説明していた。**

区間から数コマ抜いて並べる。焼き込みテロップを読んでから文言を確定させる。
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image  # noqa: E402

from clipper import config, ledger, transcript  # noqa: E402

SHOTS = 4          # 1クリップから抜くコマ数
THUMB_W = 480


def grab(src, at, dest):
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", str(at), "-i", str(src), "-frames:v", "1",
         "-vf", f"scale={THUMB_W}:-1", str(dest)],
        capture_output=True, encoding="utf-8", errors="replace")
    return dest if r.returncode == 0 and dest.exists() else None


def sheet_for(video_id, clip):
    """区間を等間隔に割ってコマを抜き、1枚に並べる。"""
    wd = config.work_dir(video_id)
    src = wd / f"{clip['clip_id']}_src.mp4"
    if not src.exists():
        print(f"- {clip['clip_id']}: {src.name} が無いので飛ばす")
        return None

    length = clip["end"] - clip["start"]
    shots = []
    for i in range(SHOTS):
        at = length * (i + 0.5) / SHOTS
        p = grab(src, at, wd / f"{clip['clip_id']}_verify_{i}.png")
        if p:
            shots.append(p)
    if not shots:
        return None

    tiles = [Image.open(p) for p in shots]
    w, h = tiles[0].size
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols + 12, h * rows + 12), (26, 26, 30))
    for i, t in enumerate(tiles):
        sheet.paste(t, (4 + (i % cols) * (w + 4), 4 + (i // cols) * (h + 4)))
    dest = wd / f"{clip['clip_id']}_verify.png"
    sheet.save(dest)
    return dest


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    video_id = sys.argv[1]
    wanted = set(sys.argv[2:])

    entry = ledger.load(video_id)
    if not entry:
        raise SystemExit(f"台帳に {video_id} がありません")

    for clip in entry["clips"]:
        if wanted and clip["clip_id"] not in wanted:
            continue
        if not (config.work_dir(video_id) / f"{clip['clip_id']}_src.mp4").exists():
            continue
        print(f"\n[{clip['clip_id']}] "
              f"{transcript.hms(clip['start'])}-{transcript.hms(clip['end'])}")
        print(f"  見出し: {clip.get('hook') or '(未設定)'}")
        print(f"  補足  : {clip.get('footer') or '(未設定)'}")
        p = sheet_for(video_id, clip)
        if p:
            print(f"  確認   : {p}")


if __name__ == "__main__":
    main()
