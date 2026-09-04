# -*- coding: utf-8 -*-
"""投稿先チャンネルの実績を YouTube Data API で実測する。

    python scripts/account_audit.py

**推測を書かない。API が返した値だけを出す。** 出るのは
チャンネルの統計と、アップロード済み全動画の再生数・公開状態・尺。
台帳（data/videos/*.json）と突き合わせて、どのクリップがどの数字かを出す。

読み取りだけなのでクォータは動画100本でも数ユニット。
認証は upload.get_service() を使い回す（CLIPPER_CREDENTIALS_DIR が要る）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clipper import ledger, upload  # noqa: E402


def iso_seconds(dur):
    """PT1M5S → 65。API の ISO8601 duration を秒に直す。"""
    n, out, cur = 0, {"H": 0, "M": 0, "S": 0}, ""
    for ch in dur.replace("PT", ""):
        if ch.isdigit():
            cur += ch
        elif ch in out:
            out[ch] = int(cur or 0)
            cur = ""
    n = out["H"] * 3600 + out["M"] * 60 + out["S"]
    return n


def fetch(service):
    ch = service.channels().list(
        part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, token = [], None
    while True:
        r = service.playlistItems().list(
            part="contentDetails", playlistId=uploads,
            maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        token = r.get("nextPageToken")
        if not token:
            break

    vids = []
    for i in range(0, len(ids), 50):
        r = service.videos().list(
            part="snippet,status,statistics,contentDetails",
            id=",".join(ids[i:i + 50])).execute()
        vids += r["items"]
    return ch, vids


def ledger_index():
    """YouTube の動画ID → (video_id, clip_id) の対応表を台帳から作る。"""
    idx = {}
    for e in ledger.all_entries():
        for c in e["clips"]:
            yt = (c.get("upload") or {}).get("youtube_video_id")
            if yt:
                idx[yt] = (e["video_id"], c["clip_id"])
    return idx


def main():
    service = upload.get_service()
    ch, vids = fetch(service)
    idx = ledger_index()

    st = ch["statistics"]
    print(f"チャンネル : {ch['snippet']['title']}（{ch['id']}）")
    print(f"登録者     : {st.get('subscriberCount')}"
          f"{'（非公開設定）' if st.get('hiddenSubscriberCount') else ''}")
    print(f"総再生数   : {st.get('viewCount')}")
    print(f"動画本数   : {st.get('videoCount')}（API が返した一覧は {len(vids)} 本）")

    vids.sort(key=lambda v: v["snippet"]["publishedAt"])
    print(f"\n{'公開日':<11}{'状態':<8}{'秒':>4}{'再生':>7}{'高評価':>7}  "
          f"{'クリップ':<24}タイトル")
    for v in vids:
        s = v["statistics"]
        sec = iso_seconds(v["contentDetails"]["duration"])
        key = idx.get(v["id"], ("?", "?"))
        print(f"{v['snippet']['publishedAt'][:10]:<11}"
              f"{v['status']['privacyStatus']:<8}"
              f"{sec:>4}{int(s.get('viewCount', 0)):>7}"
              f"{int(s.get('likeCount', 0)):>7}  "
              f"{key[0] + '/' + key[1]:<24}{v['snippet']['title'][:44]}")

    pub = [v for v in vids if v["status"]["privacyStatus"] == "public"]
    views = sorted(int(v["statistics"].get("viewCount", 0)) for v in pub)
    print(f"\n公開 {len(pub)} 本 / 非公開 {len(vids) - len(pub)} 本")
    if views:
        print(f"公開分の再生数: 合計 {sum(views)} / 中央値 {views[len(views) // 2]} "
              f"/ 最大 {views[-1]} / 最小 {views[0]}")

    # 素材（元動画）ごとの成績。どの回から採ると見られているかを見る。
    by_src = {}
    for v in pub:
        src = idx.get(v["id"], ("台帳に無い", ""))[0]
        n, tot = by_src.get(src, (0, 0))
        by_src[src] = (n + 1, tot + int(v["statistics"].get("viewCount", 0)))
    print("\n素材ごとの公開実績")
    for src, (n, tot) in sorted(by_src.items(), key=lambda kv: -kv[1][1] / kv[1][0]):
        print(f"  {src:<16} {n:>2}本  合計 {tot:>3}  1本あたり {tot / n:.1f}")

    orphan = [v for v in pub if v["id"] not in idx]
    if orphan:
        print(f"\n**台帳に紐づかない公開動画 {len(orphan)} 本**")
        for v in orphan:
            print(f"  {v['id']}  {v['snippet']['title'][:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
