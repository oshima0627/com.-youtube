# -*- coding: utf-8 -*-
"""信号を合成して切り抜き候補を出す。

tora-kirinuki からの移植。向こうの中核的な判断をそのまま採っている。

  - 単純加算にしない。**音量と反応語が同時に立つ箇所**を持ち上げる。
    片方だけなら、環境音か単なる言い回しの可能性が残る
  - 信号は点ではなく前後に三角窓で広げて足す。字幕とコメントの秒がずれても拾う
  - 区間の端は字幕キュー境界にスナップする。文の途中で切らない

向こうとの違いは組み合わせの対象。令和の虎では「音量 × 詰め語彙」だった
（笑い声がノイズ側だった）。コムドットは笑いと歓声こそが目的の場面なので、
「音量 × 歓声・驚き」を持ち上げる。
"""

# 重みは移植元の値をそのまま使わず、ヒートマップのある4本を正解として
# 実測して決めた（scripts/evaluate_signals.py）。結果は基準線との比で:
#
#   コメントのみ    1.97倍  正解を1位に当てた 2/4   ← 最良
#   語彙＋コメント  1.95倍                  1/4
#   移植元の配分    1.76倍                  0/4
#   語彙のみ        1.17倍                  0/4
#   音量のみ        0.70倍                  0/4   ← 基準線以下
#
# **音量は効かない。** 令和の虎は虎が怒鳴るので音量が盛り上がりに直結したが、
# コムドットは常時にぎやかで音量の分散が小さく、スパイクが場面の質を示さない。
# コメントに音量を足すと 3本中2本で明確に悪化したため 0 にしてある。
# 定数は残してあるので、素材が変わったら再測定して戻せる。
W_LOUD = 0.0
W_COMMENT = 0.30          # 1件でも効くようにする。唯一まともに効く信号
W_HEATMAP = 0.40          # 公開24日未満では存在しない。あれば加点

# 語彙は単独では基準線をわずかに超える程度。同点を崩す用途に留める
W_LEX = {"歓声": 0.10, "驚き": 0.05, "笑い": 0.04, "いじり": 0.03}

# 移植元の中核だった「音量 × 反応語」の同時加点も 0 にしてある。
# W_LOUD を 0 にしただけでは、この加点（0.35）が語彙の重み（最大0.10）を
# 上回るため、裏口から音量が効いて全信号の成績がコメント単独に負けていた
# （1.82倍 0/4 に対しコメント単独 1.97倍 2/4）。音量が効かない以上、
# 音量を条件に含むこの加点も成立しない。
COMBO_WINDOW = 10.0
COMBO_BONUS = 0.0
COMBO_LOUD_MIN = 0.45     # これ未満の音量は「張られた声」とみなさない
COMBO_KINDS = ("歓声", "驚き")

SPREAD = 8                # 各信号を前後何秒までなだらかに効かせるか
PREFER_BOOST = 3.0        # prefer で指定した語彙の重みを何倍にするか


def _add(grid, t, v, duration):
    """点ではなく前後に広げて足す。字幕とコメントの秒がずれても拾えるように。

    重み 0 の信号は書き込まない。書き込むと値 0 のキーで格子が埋まり、
    「信号が無い」と「重みを 0 にした」を区別できなくなる。
    """
    if not v:
        return
    for d in range(-SPREAD, SPREAD + 1):
        k = t + d
        if 0 <= k <= duration:
            grid[k] = grid.get(k, 0.0) + v * (1 - abs(d) / (SPREAD + 1))


def score_grid(signals, duration, prefer=None):
    """秒ごとのスコアを返す。値が無い秒はキーごと持たない。"""
    w_lex = dict(W_LEX)
    if prefer in w_lex:
        w_lex[prefer] *= PREFER_BOOST

    grid = {}

    loud_at = {}
    for e in signals.get("loudness") or []:
        t = int(e["t"])
        loud_at[t] = max(loud_at.get(t, 0.0), float(e["score"]))
        if e["score"] > 0:
            _add(grid, t, float(e["score"]) * W_LOUD, duration)

    hard_at = set()
    for m in signals.get("lexical") or []:
        w = w_lex.get(m["kind"], 0.0)
        if w:
            _add(grid, int(m["seconds"]), w, duration)
        if m["kind"] in COMBO_KINDS:
            hard_at.add(int(m["seconds"]))

    for m in signals.get("comment_marks") or []:
        _add(grid, int(m["seconds"]), W_COMMENT * min(m.get("count", 1), 3), duration)

    for h in signals.get("heatmap") or []:
        mid = int((h["start"] + h["end"]) / 2)
        _add(grid, mid, float(h.get("score", h.get("value", 0.0))) * W_HEATMAP, duration)

    # 音量と反応語が近接したところを持ち上げる
    for t, lv in loud_at.items():
        if lv < COMBO_LOUD_MIN:
            continue
        if any(abs(t - h) <= COMBO_WINDOW for h in hard_at):
            _add(grid, t, COMBO_BONUS * lv, duration)

    return grid


def snap_to_cues(start, end, segments):
    """区間の端を最寄りの字幕境界に寄せる。文の途中で切らないため。"""
    if not segments:
        return start, end
    times = [s["start"] for s in segments]
    nearest = lambda x: min(times, key=lambda t: abs(t - x))  # noqa: E731
    return nearest(start), nearest(end)


def signal_counts(signals, start, end):
    """区間に入っている信号の内訳。

    スコアだけでは、何によってその区間が選ばれたのかが分からない。
    歓声で取れたのか笑いの密度で取れたのかで動画の性格が変わるので、
    選ぶ前に内訳を見せる。
    """
    counts = {k: 0 for k in W_LEX}
    for m in signals.get("lexical") or []:
        if start <= m["seconds"] <= end and m["kind"] in counts:
            counts[m["kind"]] += 1
    counts["コメント"] = sum(
        m.get("count", 1) for m in (signals.get("comment_marks") or [])
        if start <= m["seconds"] <= end)
    return counts


def find_segment_candidates(signals, segments, duration, starts,
                            min_len, max_len, count=3, prefer=None):
    """企画の区切りに合わせた区間を返す。**話題をまたがない。**

    長尺をスコアの積分だけで取ると、企画の途中から始まって別の企画の途中で
    終わる切り抜きになる（実際に13分の窓が2つの企画をまたいだ）。
    区切りが取れている動画では、連続する企画のまとまりを候補にする。

    starts が空なら [] を返す。呼び出し側が窓方式へ落とす。
    """
    if not starts:
        return []

    bounds = [s["seconds"] for s in starts] + [float(duration)]
    grid = score_grid(signals, duration, prefer)

    runs = []
    for i in range(len(bounds) - 1):
        for j in range(i + 1, len(bounds)):
            start, end = bounds[i], bounds[j]
            if end - start < min_len:
                continue
            if end - start > max_len:
                break
            total = sum(grid.get(t, 0.0) for t in range(int(start), int(end)))
            runs.append((total, start, end, j - i))
    if not runs:
        return []

    runs.sort(key=lambda x: -x[0])
    picked = []
    for total, start, end, n in runs:
        if any(start < p["end"] and p["start"] < end for p in picked):
            continue
        picked.append({
            "start": start, "end": end,
            "score": round(total, 3),
            "position": round(start / duration, 3) if duration else 0.0,
            "segments": n,
            "signals": signal_counts(signals, start, end),
        })
        if len(picked) >= count:
            break
    return picked


def find_candidates(signals, segments, duration, count=5, length=60.0, prefer=None):
    """スコアの積分が大きい区間を、重ならないように上から取る。

    ヒートマップが無くても動く。コムドットでは公開24日未満の動画に
    ヒートマップが存在しないため、ここが動かないと新着で候補ゼロになる。
    """
    grid = score_grid(signals, duration, prefer)
    if not grid:
        return []

    half = int(length / 2)
    windows = []
    for center in range(half, max(half + 1, int(duration) - half), 5):
        total = sum(grid.get(t, 0.0) for t in range(center - half, center + half))
        windows.append((total, center))
    windows.sort(key=lambda x: -x[0])

    picked = []
    for total, center in windows:
        if total <= 0:
            break
        start, end = snap_to_cues(max(0.0, center - length / 2),
                                  min(float(duration), center + length / 2), segments)
        if end <= start:
            continue
        if any(start < p["end"] and p["start"] < end for p in picked):
            continue
        picked.append({
            "start": start,
            "end": end,
            "score": round(total, 3),
            "position": round(start / duration, 3) if duration else 0.0,
            "signals": signal_counts(signals, start, end),
        })
        if len(picked) >= count:
            break
    return picked
