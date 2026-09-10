# -*- coding: utf-8 -*-
"""配信が動いたかどうかの判定。**基準は先に決めてある**（config/settings.yaml）。

ここで固定したいのは1点だけ。
**「良くなった気がする」で合格にしないこと。** 判定は数値と日付だけで決まる。
"""

from datetime import date

import pytest

from clipper import distribution

# 2026-09-10 に実測した基準値と、そのとき決めた合格線。
# テストは設定ファイルの現在値に依存させない（gate のテストと同じ方針）。
TARGET = {
    "decide_after": date(2026, 9, 29),
    "min_videos": 10,
    "baseline_impressions_per_video_28d": 29,
    "baseline_shorts_feed_ratio": 0.047,
    "pass_impressions_per_video_28d": 100,
    "pass_shorts_feed_ratio": 0.20,
    "moved_multiple": 1.5,
}


def ev(metrics, today=date(2026, 9, 29)):
    return distribution.evaluate(metrics, TARGET, today)


def base(**kw):
    m = {"videos": 16, "impressions": 467, "shorts_feed_ratio": 0.047, "views": 65}
    m.update(kw)
    return m


class TestPerVideo:
    def test_割り算する(self):
        assert distribution.per_video(467, 16) == pytest.approx(29.19, abs=0.01)

    def test_本数が0なら_None(self):
        assert distribution.per_video(467, 0) is None

    def test_インプレッションが_None_なら_None(self):
        assert distribution.per_video(None, 16) is None


class TestJudgingTooEarly:
    def test_判定日より前なら_early(self):
        r = ev(base(), today=date(2026, 9, 28))
        assert r["verdict"] == "early"
        assert "2026-09-29" in " ".join(r["reasons"])

    def test_判定日当日は判定する(self):
        r = ev(base(), today=date(2026, 9, 29))
        assert r["verdict"] != "early"

    def test_早くても現在値は出す(self):
        r = ev(base(), today=date(2026, 9, 20))
        assert any("4.7%" in x for x in r["reasons"])


class TestInsufficient:
    def test_本数が足りなければ判定しない(self):
        assert ev(base(videos=9))["verdict"] == "insufficient"

    def test_フィード比率もインプレッションも無ければ判定しない(self):
        m = base(impressions=None, shorts_feed_ratio=None)
        assert ev(m)["verdict"] == "insufficient"


class TestPass:
    def test_インプレッションが合格線に届けば_pass(self):
        # 100回/本 × 34本
        assert ev(base(videos=34, impressions=3400))["verdict"] == "pass"

    def test_フィード比率が合格線に届けば_pass(self):
        assert ev(base(shorts_feed_ratio=0.20))["verdict"] == "pass"

    def test_どちらか一方で足りる(self):
        m = base(videos=34, impressions=200, shorts_feed_ratio=0.35)
        assert ev(m)["verdict"] == "pass"

    def test_インプレッションが取れなくてもフィード比率だけで_pass_になる(self):
        m = base(impressions=None, shorts_feed_ratio=0.31)
        r = ev(m)
        assert r["verdict"] == "pass"
        assert any("インプレッション" in x and "取れて" in x for x in r["reasons"])


class TestUnclear:
    def test_基準の1_5倍は超えたが合格線に届かない(self):
        # 29 * 1.5 = 43.5 → 44回/本
        assert ev(base(videos=16, impressions=704))["verdict"] == "unclear"

    def test_フィード比率が1_5倍を超えたら_unclear(self):
        assert ev(base(shorts_feed_ratio=0.08))["verdict"] == "unclear"


class TestFail:
    def test_どちらも動いていなければ_fail(self):
        r = ev(base())
        assert r["verdict"] == "fail"

    def test_fail_のときは_H1_が否定されたと言う(self):
        r = ev(base())
        assert any("H1" in x for x in r["reasons"])

    def test_わずかな増加は_fail_のまま(self):
        # 29 → 40回/本 は 1.5倍（43.5）に届かない
        assert ev(base(videos=16, impressions=640))["verdict"] == "fail"


class TestReasonsAlwaysCarryNumbers:
    @pytest.mark.parametrize("m", [
        base(), base(videos=9), base(shorts_feed_ratio=0.20),
        base(videos=16, impressions=704),
    ])
    def test_理由に必ず実測値が入る(self, m):
        r = ev(m)
        assert r["reasons"], "理由が空だと、判定を人が検算できない"
        assert any(any(c.isdigit() for c in x) for x in r["reasons"])
