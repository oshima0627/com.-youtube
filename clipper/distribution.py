# -*- coding: utf-8 -*-
"""配信（露出）が動いたかどうかを、**先に決めた基準**で判定する。

判定に使うのは2つだけ。どちらも `scripts/distribution_check.py` が実測して渡す。

- **1本あたりのサムネイルインプレッション（28日）** — 検索・ブラウジング面の露出量
- **ショートフィード経由の視聴割合** — フィードに乗っているかどうか

**インプレッションはショートフィードの露出ではない**（検索・ブラウジング面だけを数える）。
フィードに乗っているかを見るのは比率のほう。片方しか取れないこともあるので、
**どちらか一方だけでも判定できる**ようにしてある。

基準値と合格線は `config/settings.yaml` の `distribution_target`。
**あとから合格線を下げて「達成した」ことにしない。** 動かすときは理由をコミットに残すこと。
"""


def per_video(impressions, videos):
    """1本あたりのインプレッション。測れないときは None。"""
    if impressions is None or not videos:
        return None
    return impressions / videos


def _pct(x):
    return f"{x * 100:.1f}%"


def evaluate(metrics, target, today):
    """基準に対する合否を返す。

    metrics: {"videos", "impressions"(None可), "shorts_feed_ratio"(None可), "views"}
    target : settings.yaml の distribution_target（`decide_after` は date）
    today  : 判定日（date）

    verdict は5つ。

    - `early`        判定日より前。まだ判定しない
    - `insufficient` 母数が足りない／指標が1つも取れていない
    - `pass`         どちらか一方でも合格線に達した。配信は動いた
    - `unclear`      基準の n 倍は超えたが合格線に届かない。観測を延ばす
    - `fail`         どちらも動いていない。**投稿頻度が原因という仮説は否定された**
    """
    videos = metrics.get("videos") or 0
    imp = metrics.get("impressions")
    ratio = metrics.get("shorts_feed_ratio")

    ipv = per_video(imp, videos)
    reasons = []

    if ipv is not None:
        reasons.append(
            f"1本あたりインプレッション {ipv:.1f}回/28日"
            f"（基準 {target['baseline_impressions_per_video_28d']}回"
            f" / 合格線 {target['pass_impressions_per_video_28d']}回）")
    else:
        reasons.append(
            "1本あたりインプレッションは取れていない"
            "（Studio の詳細モードで読むか、--impressions で渡す）")

    if ratio is not None:
        reasons.append(
            f"ショートフィード経由 {_pct(ratio)}"
            f"（基準 {_pct(target['baseline_shorts_feed_ratio'])}"
            f" / 合格線 {_pct(target['pass_shorts_feed_ratio'])}）")
    else:
        reasons.append("ショートフィード比率は取れていない")

    if today < target["decide_after"]:
        reasons.append(
            f"判定日 {target['decide_after']:%Y-%m-%d} より前なので判定しない"
            "（在庫を出し切ってから観測する）")
        return {"verdict": "early", "reasons": reasons}

    if videos < target["min_videos"]:
        reasons.append(
            f"公開 {videos}本では判定できない（最低 {target['min_videos']}本）")
        return {"verdict": "insufficient", "reasons": reasons}

    if ipv is None and ratio is None:
        reasons.append("指標が1つも取れていないので判定できない")
        return {"verdict": "insufficient", "reasons": reasons}

    imp_pass = ipv is not None and ipv >= target["pass_impressions_per_video_28d"]
    ratio_pass = ratio is not None and ratio >= target["pass_shorts_feed_ratio"]
    if imp_pass or ratio_pass:
        reasons.append(
            "合格線に達した。**配信は動いた。**投稿頻度が効くという仮説（H1）は支持された")
        return {"verdict": "pass", "reasons": reasons}

    mult = target["moved_multiple"]
    imp_moved = (ipv is not None
                 and ipv >= target["baseline_impressions_per_video_28d"] * mult)
    ratio_moved = (ratio is not None
                   and ratio >= target["baseline_shorts_feed_ratio"] * mult)
    if imp_moved or ratio_moved:
        reasons.append(
            f"基準の{mult}倍は超えたが合格線に届かない。"
            "観測を延ばす（合格線を下げるのではなく、期間を延ばすこと）")
        return {"verdict": "unclear", "reasons": reasons}

    reasons.append(
        f"どちらも基準の{mult}倍に届いていない。"
        "**投稿頻度が原因という仮説（H1）は否定された。**"
        "次に測るのは H2（チャンネル自体の信頼度）")
    return {"verdict": "fail", "reasons": reasons}
