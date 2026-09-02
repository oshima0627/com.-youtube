# -*- coding: utf-8 -*-
"""任意の秒でコマを並べた点検シートを作る。

    python scripts/sheet_at.py <src.mp4> <dest.png> <秒> [秒 ...]

audit_third_parties.py は等間隔の6コマ固定。オーバーレイの中身など、
特定の時刻を狙って見たいときにこちらを使う。
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

W = 460


def main():
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    times = [float(t) for t in sys.argv[3:]]
    tiles = []
    for i, t in enumerate(times):
        p = dest.parent / f"_sheet_{i}.png"
        r = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-ss", str(t), "-i", str(src), "-frames:v", "1",
             "-vf", f"scale={W}:-1", str(p)], capture_output=True)
        if r.returncode == 0 and p.exists():
            tiles.append(Image.open(p))
    cols = 2 if len(tiles) <= 6 else 3
    rows = (len(tiles) + cols - 1) // cols
    w, h = tiles[0].size
    sheet = Image.new("RGB", (w * cols, h * rows), (16, 16, 16))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    sheet.save(dest)
    print(f"{len(tiles)}コマ -> {dest}")


if __name__ == "__main__":
    main()
