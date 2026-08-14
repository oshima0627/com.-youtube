# -*- coding: utf-8 -*-
"""予約投稿の計画と、その発動。

**計画を作ることと、タイマーを仕掛けることを分けてある。**
`publishAt` を設定すると YouTube が指定時刻に自動で公開する。許諾の回答が
来なくても、断られても公開される。BRDOCK へ「ご許諾をいただけた場合にのみ
公開いたします」と伝えている以上、回答前に仕掛けてはいけない。

  clipper schedule            計画を表示する（いつでも可）
  clipper schedule --arm      実際に予約を入れる（gate を通ったものだけ）

arm は publish と同じ gate を通す。permission.yaml が granted になるまで
必ず失敗する。
"""

from datetime import datetime, timedelta, timezone

import yaml

from . import config, gate, ledger

JST = timezone(timedelta(hours=9))
PLAN_PATH = config.CONFIG_DIR / "schedule.yaml"


def load_plan():
    if not PLAN_PATH.exists():
        return {"slots": []}
    with open(PLAN_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"slots": []}


def save_plan(plan):
    PLAN_PATH.write_text(
        yaml.safe_dump(plan, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    return plan


def build_plan(start_date, days=7, short_at="19:00", wide_at="20:00"):
    """在庫から1週間分の枠を組む。

    ショートを毎日1本。長尺は在庫がある日だけ、ショートの1時間後に置く。
    **ショートで見つけてもらい長尺へ送る**ので、先にショートを出す。
    """
    shorts, wides = [], []
    for e in ledger.all_entries():
        for c in e["clips"]:
            up = c.get("upload")
            if not up or c.get("excluded"):
                continue
            item = {"video_id": e["video_id"], "clip_id": c["clip_id"],
                    "youtube_video_id": up["youtube_video_id"],
                    "title": up.get("title")}
            (wides if "wide" in (c.get("formats") or []) else shorts).append(item)

    slots = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        if shorts:
            s = shorts.pop(0)
            slots.append({**s, "publish_at_jst": f"{day:%Y-%m-%d} {short_at}"})
        if wides and i == days // 2:        # 週の中ほどに1本
            w = wides.pop(0)
            slots.append({**w, "publish_at_jst": f"{day:%Y-%m-%d} {wide_at}"})

    return {"slots": slots,
            "note": "publish_at_jst は日本時間。arm するまで YouTube 側には何も入らない"}


def to_utc(jst_text):
    dt = datetime.strptime(jst_text, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def arm(plan, service=None, segments_by_video=None):
    """実際に予約を入れる。**gate を通ったものだけ。**

    privacyStatus は private のまま publishAt を仕込む。public と同時に
    送ると無視されて即時公開になる。
    """
    from . import upload

    service = service or upload.get_service()
    upload.assert_expected_channel(service)

    done, blocked = [], []
    for slot in plan["slots"]:
        entry, clip = upload.find_clip(slot["video_id"], slot["clip_id"])
        segs = (segments_by_video or {}).get(slot["video_id"])
        verdict = gate.evaluate(entry, clip, segs)
        if verdict["result"] != "pass":
            blocked.append((slot, verdict["reasons"]))
            continue

        yt_id = clip["upload"]["youtube_video_id"]
        items = service.videos().list(
            part="status", id=yt_id).execute().get("items", [])
        if not items:
            blocked.append((slot, [f"動画が見つかりません: {yt_id}"]))
            continue
        cur = items[0]["status"]
        writable = ("license", "embeddable", "publicStatsViewable",
                    "selfDeclaredMadeForKids")
        status = {k: cur[k] for k in writable if k in cur}
        status["privacyStatus"] = "private"
        status["publishAt"] = to_utc(slot["publish_at_jst"])
        service.videos().update(part="status",
                                body={"id": yt_id, "status": status}).execute()

        clip["scheduled_at"] = slot["publish_at_jst"]
        ledger.put_clips(entry, [clip])
        done.append(slot)

    return done, blocked
