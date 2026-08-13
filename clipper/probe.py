# -*- coding: utf-8 -*-
"""信号を集めて work/<video_id>/signals.json にまとめる。

音量は音声だけを落として測る。映像は候補が決まってから、その区間だけ取る。
"""

import json
import subprocess

from . import config, fetch, heatmap as heatmap_mod, signals as sig

# 8kHz モノラルに落としてから測る。音量の山を見るだけなので情報量は足りる
ASTATS_FILTER = ("astats=metadata=1:reset=8000,"
                 "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-")


def measure_loudness(audio_path):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error",
         "-i", str(audio_path), "-vn", "-ac", "1", "-ar", "8000",
         "-af", ASTATS_FILTER, "-f", "null", "-"],
        capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"音量測定に失敗しました:\n{r.stderr.strip()[-1500:]}")
    return sig.loudness_scores(sig.parse_astats(r.stdout))


def probe(video_id, with_comments=True, refresh=False):
    """4信号を集めて signals.json に書き、辞書を返す。"""
    wd = config.work_dir(video_id)
    dest = wd / "signals.json"
    if dest.exists() and not refresh:
        return json.loads(dest.read_text(encoding="utf-8"))

    # 信号が1つ欠けても他で動かす。ヒートマップは公開24日未満で必ず欠け、
    # 音声取得も 403 で落ちることがある。全部揃うことを前提にしない。
    loud = []
    try:
        loud = measure_loudness(fetch.download_audio(video_id))
    except Exception as e:                                      # noqa: BLE001
        print(f"! 音量を測れませんでした（続行）: {str(e)[:90]}")

    segments = fetch.fetch_transcript(video_id)
    lexical = sig.lexical_marks(segments)

    comments = []
    if with_comments:
        try:
            comments = fetch.fetch_comments(video_id)
        except Exception as e:                                  # noqa: BLE001
            print(f"! コメントを取得できませんでした（続行）: {str(e)[:90]}")
    marks = sig.aggregate_marks(comments)

    hm = heatmap_mod.fetch_heatmap(video_id) or []

    out = {
        "video_id": video_id,
        "loudness": loud,
        "lexical": lexical,
        "comment_marks": marks,
        "heatmap": hm,
        "comment_count": len(comments),
    }
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
