# -*- coding: utf-8 -*-
from clipper import moments, signals as sig


def seg(t, text):
    return {"start": float(t), "end": float(t) + 2.0, "text": text}


class TestFindSegmentStarts:
    def test_finds_the_announcement(self):
        segs = [seg(10, "普通の会話"),
                seg(300, "今日は挑戦ということで、本日の企画数字しりとり")]
        got = sig.find_segment_starts(segs)
        assert [x["seconds"] for x in got] == [300.0]
        assert got[0]["marker"] == "本日の企画"

    def test_finds_the_verification_variant(self):
        segs = [seg(100, "今日はチャレンジということで、本日の検証黒ひげ")]
        assert sig.find_segment_starts(segs)[0]["marker"] == "本日の検証"

    def test_merges_repeats_within_thirty_seconds(self):
        """同じ告知が数秒に渡って字幕に出るため、近接は1つにまとめる。"""
        segs = [seg(100, "本日の企画あれ"), seg(105, "本日の企画あれ"),
                seg(110, "本日の企画あれ")]
        assert len(sig.find_segment_starts(segs)) == 1

    def test_keeps_separate_announcements(self):
        segs = [seg(100, "本日の企画A"), seg(400, "本日の企画B")]
        assert len(sig.find_segment_starts(segs)) == 2

    def test_empty_when_the_video_is_a_single_project(self):
        segs = [seg(10, "催眠術をかけていきます"), seg(60, "すごいですね")]
        assert sig.find_segment_starts(segs) == []


class TestFindSegmentCandidates:
    def _signals(self):
        return {"comment_marks": [{"seconds": s, "count": 3}
                                  for s in (700, 800, 900, 2000)]}

    def test_returns_nothing_without_boundaries(self):
        """区切りが取れない動画では空を返し、呼び出し側が窓方式へ落とす。"""
        assert moments.find_segment_candidates(
            self._signals(), [], 3600, [], 600, 870) == []

    def test_candidate_edges_land_on_boundaries(self):
        starts = [{"seconds": s} for s in (0, 650, 1400, 2100)]
        got = moments.find_segment_candidates(
            self._signals(), [], 2800, starts, 600, 870, count=3)
        edges = {0, 650, 1400, 2100, 2800.0}
        for c in got:
            assert c["start"] in edges and c["end"] in edges, c

    def test_respects_the_length_window(self):
        starts = [{"seconds": s} for s in (0, 650, 1400, 2100)]
        got = moments.find_segment_candidates(
            self._signals(), [], 2800, starts, 600, 870, count=5)
        for c in got:
            assert 600 <= c["end"] - c["start"] <= 870, c

    def test_candidates_do_not_overlap(self):
        starts = [{"seconds": s} for s in (0, 650, 1400, 2100)]
        got = moments.find_segment_candidates(
            self._signals(), [], 2800, starts, 600, 870, count=5)
        for a, b in zip(got, got[1:]):
            assert a["end"] <= b["start"] or b["end"] <= a["start"]

    def test_reports_how_many_segments_are_included(self):
        starts = [{"seconds": s} for s in (0, 650, 1400)]
        got = moments.find_segment_candidates(
            self._signals(), [], 2000, starts, 600, 870, count=1)
        assert got[0]["segments"] >= 1

    def test_highest_scoring_run_comes_first(self):
        starts = [{"seconds": s} for s in (0, 650, 1400, 2100)]
        got = moments.find_segment_candidates(
            self._signals(), [], 2800, starts, 600, 870, count=3)
        assert got[0]["score"] == max(c["score"] for c in got)
