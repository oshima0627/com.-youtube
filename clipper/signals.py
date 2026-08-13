# -*- coding: utf-8 -*-
"""切り抜き地点を探すための信号を扱う純粋関数。

tora-kirinuki（令和の虎の切り抜き）で実運用された方式を移植したもの。
向こうの設計判断のうち、番組構造に依存しない部分をそのまま採り、
語彙だけコムドット用に作り直している。

**ヒートマップは主軸にできない。** コムドットの12本を実測したところ、
公開24日未満の8本には存在せず、24日以上の4本にのみ存在した（全12本が
再生50万回超なので効いているのは経過日数のみ）。切り抜きは新着を早く
出すのが勝ち筋なので、一番使いたい場面で使えない。詳細は
docs/findings-from-tora-kirinuki.md。

そこで常に取れるものを主軸に据える。

  1. 音量スパイク  盛り上がれば必ず音量に出る。新着でも即座に取れる
  2. 字幕の語彙    自動字幕の効果音タグと反応語。新着でも取れる
  3. コメント言及  件数は少ないが精度が高い
  4. ヒートマップ  あれば加点。過去回を掘るときに効く
"""

import re
import statistics

# 前後が数字やコロンでない mm:ss / h:mm:ss だけを拾う
TS_RE = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])")
SAMPLE_LIMIT = 3


# ── コメント ────────────────────────────────────────────────────────

def extract_timestamps(text):
    """コメント本文の mm:ss / h:mm:ss を秒に変換して返す。"""
    return [(int(h) if h else 0) * 3600 + int(m) * 60 + int(s)
            for h, m, s in TS_RE.findall(text or "")]


def aggregate_marks(comments):
    """秒ごとに言及を集計する。言及数の多い順、同数なら秒の小さい順。"""
    bucket = {}
    for c in comments:
        for sec in extract_timestamps(c):
            bucket.setdefault(sec, []).append(c)
    marks = [{"seconds": sec, "count": len(v), "samples": v[:SAMPLE_LIMIT]}
             for sec, v in bucket.items()]
    marks.sort(key=lambda m: (-m["count"], m["seconds"]))
    return marks


# ── 音量 ────────────────────────────────────────────────────────────

ASTATS_T_RE = re.compile(r"pts_time:([\d.]+)")
ASTATS_DB_RE = re.compile(r"lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+|-inf)")


def parse_astats(text, bin_sec=1.0):
    """ffmpeg の astats 出力を、秒ごとの平均dBにまとめる。

    無音区間は -inf になるので捨てる。
    """
    bins = {}
    cur_t = None
    for line in text.splitlines():
        m = ASTATS_T_RE.search(line)
        if m:
            cur_t = float(m.group(1))
            continue
        m = ASTATS_DB_RE.search(line)
        if m and cur_t is not None:
            if m.group(1) == "-inf":
                continue
            bins.setdefault((cur_t // bin_sec) * bin_sec, []).append(float(m.group(1)))
    return [{"t": t, "db": statistics.fmean(v)} for t, v in sorted(bins.items())]


def loudness_scores(env, baseline_sec=120.0):
    """局所的な基準からどれだけ跳ねたかを 0..1 で返す。

    絶対的な音量ではなく**周囲との差**を見る。全体が大きい動画でも
    静かな動画でも、同じ尺度で「ここで声が張られた」を拾える。
    """
    if not env:
        return []
    half = max(1, int(baseline_sec / 2))
    out = []
    for i, e in enumerate(env):
        lo, hi = max(0, i - half), min(len(env), i + half + 1)
        base = statistics.median(x["db"] for x in env[lo:hi])
        out.append({"t": e["t"], "db": e["db"], "over": e["db"] - base})

    peak = max((o["over"] for o in out), default=0.0)
    if peak <= 0:
        return [{"t": o["t"], "score": 0.0} for o in out]
    return [{"t": o["t"], "score": max(0.0, o["over"]) / peak} for o in out]


# ── 字幕の語彙 ──────────────────────────────────────────────────────

# 令和の虎は「持ち込む→詰める→判定」という定型構造を持つので語彙で山が取れた。
# コムドットにその構造は無い。代わりに使えるのが**自動字幕の効果音タグ**で、
# 実測では 58 分の回に [笑い]96 / [拍手]6 / [叫び声]3、82 分の回に
# [笑い]105 / [叫び声]50 / [拍手]10 / [大歓声]7 が入っていた。
#
# [笑い] は 35 秒に 1 回の頻度で出るため単独では効かない。重みを下げ、
# 密度として効かせる。逆に [叫び声][大歓声][拍手] は稀なので強く見る。
LEXICON = {
    "歓声": ("[叫び声]", "[大歓声]", "[拍手]"),
    "笑い": ("[笑い]",),
    "驚き": ("マジ", "まじ", "やばい", "ヤバ", "嘘だろ", "うそ", "ウソ",
             "ちょっと待って", "どういうこと", "すご", "怖", "こわ", "無理"),
    "いじり": ("お前", "ふざけ", "最悪", "ひどい", "やめろ"),
}


def lexical_marks(segments, lexicon=None):
    """字幕から語彙・効果音タグを拾う。[{"seconds","kind","word","line"}, ...]

    segments は fetch.fetch_transcript の [{start, end, text}] を受ける。
    """
    lex = lexicon or LEXICON
    out = []
    for s in segments:
        line = s.get("text") or ""
        for kind, words in lex.items():
            hit = next((w for w in words if w in line), None)
            if hit:
                out.append({"seconds": int(s.get("start") or 0), "kind": kind,
                            "word": hit, "line": line})
    return out
