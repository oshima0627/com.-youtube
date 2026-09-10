# -*- coding: utf-8 -*-
"""配信（露出）が動いたかを、**先に決めた基準**で判定する。

    python scripts/distribution_check.py
    python scripts/distribution_check.py --impressions 467   # Studio から手で渡す

09-02 と 09-10 は Studio をブラウザで開いて手で読んだ。毎回それをやると
測る前に疲れるので、取れるものは API から取る。

**取れるもの / 取れないもの**

- ショートフィード経由の視聴割合 … YouTube Analytics API の
  `insightTrafficSourceType` から取れる。**判定の主役はこちら**
- サムネイルのインプレッション … Analytics API で返らないことがある。
  返らなければ `--impressions` で Studio の値を渡す。渡さなくても
  フィード比率だけで判定は出る

**インプレッションはフィードの露出ではない**（検索・ブラウジング面だけを数える）。
フィードに乗ったかどうかを見るのは比率のほう。

Analytics には集計の遅れがあるので、既定では **2日前までの28日間**を見る。
認証は `python -m clipper auth --analytics`（投稿用の token.json とは別トークン）。
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from clipper import config, distribution, upload  # noqa: E402

# ショートフィードの流入。API 側の呼び名が変わりうるので候補で持つ。
# 該当が1つも無ければ「0件」ではなく「取れなかった」として扱う。
SHORTS_FEED_KEYS = {"SHORTS", "SHORTS_FEED"}

# サムネイルのインプレッション。Analytics API に無いことがあるので順に試す。
IMPRESSION_METRICS = ["impressions", "thumbnailImpressions"]


def window(days=28, lag=2):
    end = date.today() - timedelta(days=lag)
    return end - timedelta(days=days - 1), end


def query(service, channel_id, start, end, **kw):
    return service.reports().query(
        ids=f"channel=={channel_id}",
        startDate=f"{start:%Y-%m-%d}", endDate=f"{end:%Y-%m-%d}", **kw).execute()


def traffic_sources(service, channel_id, start, end):
    """流入経路ごとの視聴回数。{"YT_SEARCH": 54, ...}"""
    r = query(service, channel_id, start, end,
              dimensions="insightTrafficSourceType", metrics="views",
              sort="-views")
    return {row[0]: row[1] for row in (r.get("rows") or [])}


def impressions(service, channel_id, start, end):
    """サムネイルのインプレッション。API が返さなければ (None, 理由)。"""
    last = None
    for metric in IMPRESSION_METRICS:
        try:
            r = query(service, channel_id, start, end, metrics=metric)
        except Exception as e:                                 # noqa: BLE001
            last = f"{metric}: {e}"
            continue
        rows = r.get("rows") or []
        if rows:
            return int(rows[0][0]), None
        last = f"{metric}: 行が返らなかった"
    return None, last


def public_video_count():
    """公開本数。Data API 側（従来の token.json）から数える。"""
    service = upload.get_service()
    ch = service.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while True:
        r = service.playlistItems().list(
            part="contentDetails", playlistId=uploads,
            maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        token = r.get("nextPageToken")
        if not token:
            break
    n = 0
    for i in range(0, len(ids), 50):
        r = service.videos().list(part="status", id=",".join(ids[i:i + 50])).execute()
        n += sum(1 for v in r["items"] if v["status"]["privacyStatus"] == "public")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impressions", type=int,
                    help="Studio の詳細モードで読んだインプレッション数を手で渡す")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--videos", type=int, help="公開本数を手で渡す（API を呼ばない）")
    args = ap.parse_args()

    settings = config.settings()
    channel_id = settings["channel"]["expected_channel_id"]
    target = settings["distribution_target"]
    start, end = window(args.days)

    try:
        service = upload.get_analytics_service()
    except upload.UploadBlocked as e:
        print(f"× {e}", file=sys.stderr)
        print(f"\n  ブラウザで読むなら（**?authuser=1 が要る**）:\n"
              f"  https://studio.youtube.com/channel/{channel_id}"
              f"/analytics/tab-content/period-default?authuser=1", file=sys.stderr)
        return 1

    print(f"期間: {start:%Y-%m-%d} 〜 {end:%Y-%m-%d}（{args.days}日・集計遅れを2日見込む）")

    sources = traffic_sources(service, channel_id, start, end)
    total = sum(sources.values())
    feed = sum(v for k, v in sources.items() if k in SHORTS_FEED_KEYS)
    ratio = (feed / total) if total else None

    print(f"視聴回数 {total}")
    for k, v in sources.items():
        mark = " ← ショートフィード" if k in SHORTS_FEED_KEYS else ""
        print(f"  {k:<24}{v:>6}  {v / total * 100:5.1f}%{mark}" if total
              else f"  {k:<24}{v:>6}{mark}")
    if not any(k in SHORTS_FEED_KEYS for k in sources):
        print("  （ショートフィードの行が無い。0回か、API の呼び名が変わったかのどちらか）")

    imp, why = (args.impressions, None)
    if imp is None:
        imp, why = impressions(service, channel_id, start, end)
    if imp is None:
        print(f"インプレッション: 取れなかった（{why}）")
        print("  → Studio の詳細モードで読んで --impressions で渡してください")
    else:
        print(f"インプレッション {imp}")

    videos = args.videos if args.videos is not None else public_video_count()
    print(f"公開本数 {videos}")

    r = distribution.evaluate(
        {"videos": videos, "impressions": imp,
         "shorts_feed_ratio": ratio, "views": total},
        target, date.today())
    print(f"\n判定: {r['verdict'].upper()}")
    for x in r["reasons"]:
        print(f"  - {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
