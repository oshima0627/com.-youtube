# -*- coding: utf-8 -*-
from clipper import moments


def seg(t):
    return {"start": float(t), "end": float(t) + 1.0, "text": "x"}


class TestScoreGrid:
    def test_empty_signals_give_empty_grid(self):
        assert moments.score_grid({}, 600) == {}

    def test_signal_spreads_to_neighbours(self):
        grid = moments.score_grid({"lexical": [{"seconds": 100, "kind": "歓声"}]}, 600)
        assert grid[100] > grid[104] > grid[108]
        assert 100 + moments.SPREAD + 1 not in grid

    def test_spread_is_clamped_to_video_bounds(self):
        grid = moments.score_grid({"lexical": [{"seconds": 1, "kind": "歓声"}]}, 600)
        assert min(grid) == 0

    def test_laughter_is_weighted_below_cheering(self):
        """[笑い] は 35 秒に 1 回出るので、単独では効かせない。"""
        cheer = moments.score_grid({"lexical": [{"seconds": 50, "kind": "歓声"}]}, 600)
        laugh = moments.score_grid({"lexical": [{"seconds": 50, "kind": "笑い"}]}, 600)
        assert cheer[50] > laugh[50]

    def test_prefer_boosts_the_named_kind(self):
        plain = moments.score_grid({"lexical": [{"seconds": 50, "kind": "笑い"}]}, 600)
        boosted = moments.score_grid({"lexical": [{"seconds": 50, "kind": "笑い"}]},
                                     600, prefer="笑い")
        assert boosted[50] == plain[50] * moments.PREFER_BOOST

    def test_comment_marks_saturate_at_three(self):
        g3 = moments.score_grid({"comment_marks": [{"seconds": 50, "count": 3}]}, 600)
        g9 = moments.score_grid({"comment_marks": [{"seconds": 50, "count": 9}]}, 600)
        assert g3[50] == g9[50]

    def test_heatmap_accepts_either_key(self):
        a = moments.score_grid({"heatmap": [{"start": 40, "end": 60, "score": 1.0}]}, 600)
        b = moments.score_grid({"heatmap": [{"start": 40, "end": 60, "value": 1.0}]}, 600)
        assert a == b


class TestLoudnessIsDisabled:
    """音量まわりは実測で効かないと分かったため既定で無効。

    仕組みは残してあるので、無効になっていること自体を固定しておく。
    素材が変わって再測定するときは、ここを見れば何を戻せばよいか分かる。
    """

    def test_loudness_weight_is_zero_by_default(self):
        assert moments.W_LOUD == 0.0

    def test_combo_bonus_is_zero_by_default(self):
        # W_LOUD だけ 0 にしてもこの加点が語彙の重みを上回り、
        # 裏口から音量が効いて成績が落ちた。両方 0 にして初めて解消した
        assert moments.COMBO_BONUS == 0.0
        assert moments.COMBO_BONUS < min(moments.W_LEX.values()) or moments.COMBO_BONUS == 0.0

    def test_loudness_alone_contributes_nothing(self):
        assert moments.score_grid({"loudness": [{"t": 100, "score": 1.0}]}, 600) == {}


class TestComboMechanism:
    """加点そのものは動く。再有効化したときに壊れていないことを担保する。"""

    def _signals(self, gap):
        return {
            "loudness": [{"t": 100, "score": 1.0}],
            "lexical": [{"seconds": 100 + gap, "kind": "歓声"}],
        }

    def test_bonus_applies_when_enabled(self, monkeypatch):
        monkeypatch.setattr(moments, "COMBO_BONUS", 0.35)
        lex_only = moments.score_grid({"lexical": [{"seconds": 100, "kind": "歓声"}]}, 600)
        assert moments.score_grid(self._signals(0), 600)[100] > lex_only[100]

    def test_no_bonus_when_far_apart(self, monkeypatch):
        monkeypatch.setattr(moments, "COMBO_BONUS", 0.35)
        near = moments.score_grid(self._signals(0), 600)
        far = moments.score_grid(self._signals(int(moments.COMBO_WINDOW) + 5), 600)
        # 音量の重みが 0 なので、離れている側は 100 秒地点にキーを持たない
        assert near[100] > far.get(100, 0.0)

    def test_quiet_moments_get_no_bonus(self, monkeypatch):
        monkeypatch.setattr(moments, "COMBO_BONUS", 0.35)
        quiet = moments.score_grid({
            "loudness": [{"t": 100, "score": moments.COMBO_LOUD_MIN - 0.01}],
            "lexical": [{"seconds": 100, "kind": "歓声"}],
        }, 600)
        lex_only = moments.score_grid({"lexical": [{"seconds": 100, "kind": "歓声"}]}, 600)
        assert quiet[100] == lex_only[100]

    def test_laughter_alone_does_not_trigger_the_bonus(self, monkeypatch):
        """笑いは頻出なので、組み合わせの対象は歓声と驚きに限る。"""
        monkeypatch.setattr(moments, "COMBO_BONUS", 0.35)
        s = {"loudness": [{"t": 100, "score": 1.0}],
             "lexical": [{"seconds": 100, "kind": "笑い"}]}
        lex_only = moments.score_grid({"lexical": [{"seconds": 100, "kind": "笑い"}]}, 600)
        assert moments.score_grid(s, 600)[100] == lex_only[100]


class TestSnapToCues:
    def test_snaps_to_nearest_boundary(self):
        segs = [seg(0), seg(10), seg(25)]
        assert moments.snap_to_cues(9.0, 24.0, segs) == (10.0, 25.0)

    def test_without_segments_returns_input(self):
        assert moments.snap_to_cues(3.0, 9.0, []) == (3.0, 9.0)

    def test_snapping_may_extend_when_no_limit_is_given(self):
        segs = [seg(0), seg(10), seg(70)]
        assert moments.snap_to_cues(10.0, 65.0, segs) == (10.0, 70.0)

    def test_does_not_exceed_the_limit(self):
        """境界へ寄せた結果が上限を超えないこと。

        これが無いと設定した尺を静かに超える。実際に上限58秒の設定で
        65秒の動画が上がっていた。
        """
        segs = [seg(0), seg(10), seg(50), seg(70)]
        start, end = moments.snap_to_cues(10.0, 65.0, segs, max_len=58)
        assert end - start <= 58
        assert end == 50.0          # 収まる範囲で最も後ろの境界

    def test_falls_back_to_the_hard_edge_when_no_boundary_fits(self):
        segs = [seg(0), seg(10), seg(200)]
        start, end = moments.snap_to_cues(10.0, 190.0, segs, max_len=58)
        assert (start, end) == (10.0, 68.0)

    def test_candidates_respect_the_configured_length(self):
        signals = {"comment_marks": [{"seconds": 300, "count": 3}]}
        segs = [seg(t) for t in range(0, 600, 7)]      # 端数のある境界
        for c in moments.find_candidates(signals, segs, 600, count=3, length=58):
            assert c["end"] - c["start"] <= 58, c


class TestFindCandidates:
    def test_no_signals_gives_no_candidates(self):
        assert moments.find_candidates({}, [seg(0)], 600) == []

    def test_works_without_heatmap(self):
        """公開24日未満の動画にはヒートマップが無い。ここが動かないと候補ゼロになる。"""
        signals = {"loudness": [{"t": 300, "score": 1.0}],
                   "lexical": [{"seconds": 300, "kind": "歓声"}]}
        got = moments.find_candidates(signals, [seg(t) for t in range(0, 600, 5)], 600)
        assert got and got[0]["start"] <= 300 <= got[0]["end"]

    def test_candidates_do_not_overlap(self):
        signals = {"lexical": [{"seconds": s, "kind": "歓声"}
                               for s in (100, 300, 500, 700, 900)]}
        segs = [seg(t) for t in range(0, 1000, 5)]
        got = moments.find_candidates(signals, segs, 1000, count=5, length=60)
        for a, b in zip(got, got[1:]):
            assert a["end"] <= b["start"] or b["end"] <= a["start"]

    def test_reports_position_and_breakdown(self):
        signals = {"lexical": [{"seconds": 800, "kind": "歓声"}],
                   "comment_marks": [{"seconds": 800, "count": 2}]}
        got = moments.find_candidates(signals, [seg(t) for t in range(0, 1000, 5)],
                                      1000, count=1, length=60)
        assert got[0]["position"] > 0.7          # 終盤に寄っていることが分かる
        assert got[0]["signals"]["歓声"] == 1
        assert got[0]["signals"]["コメント"] == 2
