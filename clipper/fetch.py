# -*- coding: utf-8 -*-
"""動画のメタ情報・字幕・指定区間の取得。

yt-dlp は Python API ではなく CLI を subprocess で呼ぶ。JS ランタイムの指定など
オプションの挙動が CLI 側でしか検証できていないため、確実な方を採る。

動画本体は「使う区間だけ」を落とす。全編を保存しないことで、ディスクの消費と
手元に置く複製の量の両方を最小にする。
"""

import json
import subprocess
import sys
from pathlib import Path

from . import config

# yt-dlp が YouTube の抽出に必要とする JS ランタイム
YTDLP = [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node"]

# 公開動画以外は扱わない。特に subscriber_only（メンバーシップ限定）は
# 有料コンテンツであり、切り抜きの対象にしてはならない。
ALLOWED_AVAILABILITY = {"public"}


class NotClippable(Exception):
    """素材として使ってはいけない動画。"""


# メンバーシップ限定動画は yt-dlp がメタ情報の取得自体に失敗するため、
# availability を見る前に stderr で判定する必要がある。
MEMBERS_ONLY_MARKERS = ("available to this channel's members", "members-only")


def _run(args):
    r = subprocess.run(YTDLP + args, capture_output=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        err = r.stderr.strip()
        if any(m in err for m in MEMBERS_ONLY_MARKERS):
            raise NotClippable("メンバーシップ限定動画のため対象外です")
        raise RuntimeError(f"yt-dlp が失敗しました:\n{err[-2000:]}")
    return r.stdout


def url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_meta(video_id):
    """メタ情報を取得する。公開動画でなければ NotClippable を投げる。"""
    raw = _run(["--dump-single-json", "--skip-download", url(video_id)])
    info = json.loads(raw)

    availability = info.get("availability") or "unknown"
    if availability not in ALLOWED_AVAILABILITY:
        raise NotClippable(
            f"{video_id} は availability={availability} のため対象外です。"
            "メンバーシップ限定・限定公開・非公開の動画は切り抜かない。")

    return {
        "title": info.get("title"),
        "description": (info.get("description") or "")[:4000],
        "duration": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "availability": availability,
        "channel": info.get("channel"),
        "channel_id": info.get("channel_id"),
    }


def fetch_transcript(video_id, lang="ja-orig"):
    """自動字幕を取得し、[{start, end, text}] に正規化して返す。

    YouTube の自動字幕を使うため Whisper は不要。取得済みなら再取得しない。
    """
    wd = config.work_dir(video_id)
    normalized = wd / "transcript.json"
    if normalized.exists():
        with open(normalized, encoding="utf-8") as f:
            return json.load(f)

    _run(["--write-auto-subs", "--sub-langs", lang, "--sub-format", "json3",
          "--skip-download", "-o", str(wd / "sub"), url(video_id)])

    raw_files = list(wd.glob(f"sub.{lang}.json3"))
    if not raw_files:
        raise RuntimeError(f"{video_id} の字幕 ({lang}) を取得できませんでした")

    with open(raw_files[0], encoding="utf-8") as f:
        events = json.load(f).get("events", [])

    segments = []
    for e in events:
        text = "".join(s.get("utf8", "") for s in e.get("segs", [])).strip()
        if not text or text == "\n":
            continue
        start = e.get("tStartMs", 0) / 1000
        segments.append({
            "start": round(start, 2),
            "end": round(start + e.get("dDurationMs", 0) / 1000, 2),
            "text": text.replace("\n", " "),
        })

    with open(normalized, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=1)
    return segments


def download_audio(video_id, dest: Path = None):
    """音量測定用に音声だけを落とす。映像は要らないので全編でも軽い。"""
    dest = dest or (config.work_dir(video_id) / "audio.m4a")
    if dest.exists():
        return dest
    _run(["-f", "ba[ext=m4a]/ba", "-o", str(dest.with_suffix("")) + ".%(ext)s",
          url(video_id)])
    if not dest.exists():
        found = list(dest.parent.glob(f"{dest.stem}.*"))
        if not found:
            raise RuntimeError(f"音声の取得に失敗しました: {dest}")
        return found[0]
    return dest


def fetch_comments(video_id, limit=400):
    """コメント本文を取る。タイムスタンプ言及の集計に使う。"""
    from yt_dlp import YoutubeDL

    opts = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        "getcomments": True,
        "extractor_args": {"youtube": {
            "lang": ["ja"],
            "max_comments": [str(limit), "all", "0"],
            "comment_sort": ["top"],
        }},
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url(video_id), download=False)
    return [c.get("text") or "" for c in (info.get("comments") or [])]


# googlevideo の CDN が断続的に 403 を返す。URL は一定時間で失効し、取り直せば
# 通ることが多い。長尺ほど転送時間が長く当たりやすいので、黙って諦めない。
TRANSIENT_MARKERS = ("403", "Forbidden", "timed out", "Connection reset",
                     "Remote end closed")
DOWNLOAD_ATTEMPTS = 4


def download_section(video_id, start, end, dest: Path, attempts=DOWNLOAD_ATTEMPTS):
    """指定区間だけを落とす。全編は保存しない。

    一時エラーは取り直す。無人運転では、1回の 403 で止まると何も出なくなる。
    """
    if dest.exists():
        return dest

    last = None
    for attempt in range(1, attempts + 1):
        try:
            _run(["--download-sections", f"*{start}-{end}",
                  "--force-keyframes-at-cuts",
                  "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]",
                  "--merge-output-format", "mp4",
                  "-o", str(dest.with_suffix("")) + ".%(ext)s", url(video_id)])
        except RuntimeError as e:
            last = e
            if not any(m in str(e) for m in TRANSIENT_MARKERS):
                raise
            print(f"! 取得に失敗（{attempt}/{attempts}）。取り直します")
            for leftover in dest.parent.glob(f"{dest.stem}.*"):
                leftover.unlink(missing_ok=True)
            continue
        if dest.exists():
            return dest
        last = RuntimeError(f"区間の取得に失敗しました: {dest}")

    raise last
