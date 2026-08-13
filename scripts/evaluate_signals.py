# -*- coding: utf-8 -*-
"""信号の組み合わせを、ヒートマップを正解として評価する。

    python scripts/evaluate_signals.py <video_id> [<video_id> ...]

ヒートマップが存在する動画（公開24日以上）でのみ実行できる。
ヒートマップを候補算出から外して候補を出し、その区間の実ヒート値で採点する。
どの信号が効いているかを、思い込みではなく数字で決めるための道具。
"""

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows のコンソールは既定が cp932 で、記号や日本語で落ちる
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clipper import fetch, moments, probe, transcript  # noqa: E402

COMBOS = [
    ("全信号", ("loudness", "lexical", "comment_marks")),
    ("音量のみ", ("loudness",)),
    ("語彙のみ", ("lexical",)),
    ("コメントのみ", ("comment_marks",)),
    ("音量＋コメント", ("loudness", "comment_marks")),
    ("語彙＋コメント", ("lexical", "comment_marks")),
]


def evaluate(video_id, count=3, length=60.0):
    signals = probe.probe(video_id)
    hm = signals.get("heatmap") or []
    if not hm:
        return None

    segments = fetch.fetch_transcript(video_id)
    duration = int(max(s["end"] for s in segments))
    best = max(hm, key=lambda h: h["value"])
    truth = (best["start"] + best["end"]) / 2
    baseline = statistics.fmean(h["value"] for h in hm)

    def heat(a, b):
        v = [h["value"] for h in hm if h["end"] > a and h["start"] < b]
        return statistics.fmean(v) if v else 0.0

    rows = []
    for name, keys in COMBOS:
        sub = {k: (signals[k] if k in keys else [])
               for k in ("loudness", "lexical", "comment_marks", "heatmap")}
        cands = moments.find_candidates(sub, segments, duration,
                                        count=count, length=length)
        if not cands:
            rows.append({"name": name, "top_mean": 0.0, "first": 0.0, "hit": None})
            continue
        hits = [i for i, c in enumerate(cands, 1) if c["start"] <= truth <= c["end"]]
        rows.append({
            "name": name,
            "top_mean": statistics.fmean(heat(c["start"], c["end"]) for c in cands),
            "first": heat(cands[0]["start"], cands[0]["end"]),
            "hit": hits[0] if hits else None,
        })

    return {"video_id": video_id, "baseline": baseline,
            "truth": truth, "rows": rows}


def main():
    ids = sys.argv[1:]
    if not ids:
        raise SystemExit(__doc__)

    results = []
    for v in ids:
        r = evaluate(v)
        if r is None:
            print(f"- {v}: ヒートマップが無いため評価できません（公開24日未満）")
            continue
        results.append(r)

    lines = []
    for r in results:
        lines.append(f"## {r['video_id']}  正解 {transcript.hms(r['truth'])} / "
                     f"基準線 {r['baseline']:.3f}")
        lines.append("")
        lines.append("| 信号 | 上位3の平均ヒート | 1位のヒート | 正解の順位 |")
        lines.append("|---|---:|---:|---|")
        for row in r["rows"]:
            lines.append(f"| {row['name']} | {row['top_mean']:.3f} | "
                         f"{row['first']:.3f} | {row['hit'] or 'なし'} |")
        lines.append("")

    if len(results) > 1:
        lines.append("## 全動画の平均（基準線との比）")
        lines.append("")
        lines.append("| 信号 | 上位3平均/基準線 | 正解を当てた本数 |")
        lines.append("|---|---:|---:|")
        for i, (name, _) in enumerate(COMBOS):
            ratios = [r["rows"][i]["top_mean"] / r["baseline"] for r in results]
            hits = sum(1 for r in results if r["rows"][i]["hit"] == 1)
            lines.append(f"| {name} | {statistics.fmean(ratios):.2f}倍 | "
                         f"{hits}/{len(results)} |")

    out = Path(__file__).resolve().parents[1] / "work" / "signal_evaluation.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ {out}")


if __name__ == "__main__":
    main()
