# -*- coding: utf-8 -*-
"""パイプラインをまとめて回す。

    python -m clipper run <video_id>      素材確認→信号収集→候補→ゲート→書き出し
    python -m clipper candidates <video_id>  候補だけ見る
    python -m clipper held                保留されたクリップと理由の一覧
    python -m clipper status              全体の状態

投稿はここには無い。ゲートを通っていても、許諾の回答が来るまで
publish は実装しない方針のため。
"""

import argparse
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from . import (config, fetch, gate, ledger, metadata, moments,  # noqa: E402
               probe, render, schedule as schedule_mod, screen, transcript,
               upload)


def cmd_run(args):
    vid = args.video_id

    verdict = screen.screen(vid)
    if not verdict["ok"]:
        print(f"× {vid} は素材にできません")
        for r in verdict["reasons"]:
            print(f"    - {r}")
            return 1

    meta = verdict["meta"]
    duration = meta.get("duration") or 0
    print(f"○ {meta['title'][:56]}  ({transcript.hms(duration)})")

    entry = ledger.create(vid, meta)
    segments = fetch.fetch_transcript(vid)
    ledger.set_state(entry, "transcribed")

    signals = probe.probe(vid)
    print(f"  信号: コメント言及 {len(signals['comment_marks'])}箇所 / "
          f"語彙 {len(signals['lexical'])}件 / "
          f"ヒートマップ {len(signals['heatmap'])}区間")
    ledger.set_state(entry, "extracted")

    length = config.settings()["formats"]["short"]["max_seconds"]
    cands = moments.find_candidates(signals, segments, duration,
                                    count=args.count, length=length,
                                    prefer=args.prefer)
    if not cands:
        print("  候補なし")
        return 1

    clips = []
    for i, c in enumerate(cands, 1):
        clip = {
            "clip_id": f"auto{i:02d}",
            "start": c["start"], "end": c["end"],
            "duration": round(c["end"] - c["start"], 1),
            "score": c["score"], "position": c["position"],
            "signals": c["signals"],
            "formats": [], "published": None,
        }
        clip["gate"] = gate.evaluate(entry, clip, segments)
        clips.append(clip)

    ledger.put_clips(entry, clips)
    ledger.set_state(entry, "gated")

    print()
    for i, c in enumerate(clips, 1):
        g = c["signals"]
        mark = "通過" if c["gate"]["result"] == "pass" else "保留"
        print(f"  {i}. {transcript.hms(c['start'])}-{transcript.hms(c['end'])}"
              f"  {c['position']:.0%}地点  score={c['score']:.1f}"
              f"  [コメント{g['コメント']} 歓声{g['歓声']} 驚き{g['驚き']} 笑い{g['笑い']}]  {mark}")
        for r in c["gate"]["reasons"]:
            print(f"       └ {r}")

    if args.no_render:
        return 0

    print()
    out = config.out_dir()
    wd = config.work_dir(vid)
    for c in clips[:args.render]:
        src = wd / f"{c['clip_id']}_src.mp4"
        dest = wd / f"{vid}_{c['clip_id']}_short.mp4"
        try:
            fetch.download_section(vid, c["start"], c["end"], src)
            render.render_short(src, dest)
        except Exception as e:                                  # noqa: BLE001
            print(f"  ! {c['clip_id']} の書き出しに失敗: {str(e)[:100]}")
            continue
        shutil.move(str(dest), out / dest.name)
        c["formats"] = ["short"]
        print(f"  ✓ out/{dest.name}  ({(out / dest.name).stat().st_size // 1024} KB)")

    ledger.put_clips(entry, clips)
    ledger.set_state(entry, "rendered")
    return 0


def cmd_candidates(args):
    args.no_render, args.render = True, 0
    return cmd_run(args)


def cmd_held(args):
    """保留されたクリップと理由。**人が触る唯一の口。**"""
    found = 0
    for entry in ledger.all_entries():
        held = [c for c in entry["clips"] if (c.get("gate") or {}).get("result") == "held"]
        if not held:
            continue
        print(f"\n{entry['video_id']}  {(entry.get('meta') or {}).get('title', '')[:50]}")
        for c in held:
            found += 1
            print(f"  {c['clip_id']}  {transcript.hms(c['start'])}-{transcript.hms(c['end'])}")
            for r in c["gate"]["reasons"]:
                print(f"       └ {r}")
    print(f"\n保留 {found} 件")
    return 0


def cmd_status(args):
    rt = gate.load_runtime()
    perm = config.permission()
    print(f"許諾ステータス : {perm.get('status')}（{perm.get('requested_at')} に依頼）")
    print(f"キルスイッチ   : {'ON ' + str(rt.get('kill_reason')) if rt.get('kill_switch') else 'OFF'}")
    published = sum(len(v) for v in rt["published"].values())
    print(f"投稿済み       : {published} 本")
    entries = list(ledger.all_entries())
    clips = [c for e in entries for c in e["clips"]]
    rendered = [c for c in clips if c.get("formats")]
    print(f"台帳           : 動画 {len(entries)} 本 / クリップ {len(clips)} 件"
          f"（書き出し済み {len(rendered)}）")
    return 0


def cmd_auth(args):
    return upload.cmd_auth(args)


def cmd_upload(args):
    try:
        info = upload.upload_private(args.video_id, args.clip_id, args.title)
    except (upload.UploadBlocked, metadata.InvalidTitle) as e:
        print(f"× {e}", file=sys.stderr)
        return 1
    print(f"✓ 非公開でアップロードしました: {info['url']}")
    print(f"  チャンネル: {info['channel_title']}（{info['channel_id']}）")
    print("  公開するには許諾の回答を待ち、permission.yaml を granted にしてから")
    print(f"  python -m clipper publish {args.video_id} {args.clip_id}")
    return 0


def cmd_publish(args):
    segments = fetch.fetch_transcript(args.video_id)
    try:
        info = upload.publish(args.video_id, args.clip_id, segments=segments)
    except upload.UploadBlocked as e:
        print(f"× {e}", file=sys.stderr)
        return 1
    print(f"✓ 公開しました: {info['url']}")
    return 0


def cmd_schedule(args):
    plan = schedule_mod.load_plan()
    if args.rebuild or not plan["slots"]:
        from datetime import date, timedelta
        plan = schedule_mod.build_plan(date.today() + timedelta(days=1), args.days)
        schedule_mod.save_plan(plan)

    print(f"予約計画  {len(plan['slots'])}枠")
    print()
    for s in plan["slots"]:
        print(f"  {s['publish_at_jst']}  {s['video_id']}/{s['clip_id']}")
        print(f"      {s.get('title', '')}")

    if not args.arm:
        print()
        print("実際の予約は入っていません。--arm で発動します。")
        return 0

    done, blocked = schedule_mod.arm(plan)
    print()
    print(f"予約した: {len(done)}件")
    for s, reasons in blocked:
        print(f"× {s['video_id']}/{s['clip_id']}")
        for r in reasons:
            print(f"    - {r}")
    return 0 if not blocked else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="clipper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("run", "candidates"):
        p = sub.add_parser(name)
        p.add_argument("video_id")
        p.add_argument("--count", type=int, default=5)
        p.add_argument("--render", type=int, default=2, help="上位何件を書き出すか")
        p.add_argument("--no-render", action="store_true")
        p.add_argument("--prefer", choices=["歓声", "驚き", "笑い", "いじり"])
        p.set_defaults(func=cmd_run if name == "run" else cmd_candidates)

    sub.add_parser("held").set_defaults(func=cmd_held)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("auth").set_defaults(func=cmd_auth)

    p = sub.add_parser("schedule", help="予約投稿の計画と発動")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--rebuild", action="store_true", help="計画を組み直す")
    p.add_argument("--arm", action="store_true", help="実際に予約を入れる")
    p.set_defaults(func=cmd_schedule)

    p = sub.add_parser("upload", help="非公開でアップロードする")
    p.add_argument("video_id")
    p.add_argument("clip_id")
    p.add_argument("--title", required=True)
    p.set_defaults(func=cmd_upload)

    p = sub.add_parser("publish", help="非公開の動画を公開に切り替える（ゲート必須）")
    p.add_argument("video_id")
    p.add_argument("clip_id")
    p.set_defaults(func=cmd_publish)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
