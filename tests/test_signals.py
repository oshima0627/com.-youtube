# -*- coding: utf-8 -*-
from clipper import signals as sig


class TestExtractTimestamps:
    def test_mm_ss(self):
        assert sig.extract_timestamps("12:34 ここ好き") == [754]

    def test_h_mm_ss(self):
        assert sig.extract_timestamps("1:02:03 から") == [3723]

    def test_multiple(self):
        assert sig.extract_timestamps("3:00 と 4:30") == [180, 270]

    def test_ignores_numbers_that_are_not_times(self):
        # 前後に数字やコロンが続くものは時刻ではない
        assert sig.extract_timestamps("12:34:56:78") == []

    def test_empty(self):
        assert sig.extract_timestamps("") == []
        assert sig.extract_timestamps(None) == []


class TestAggregateMarks:
    def test_counts_and_sorts_by_frequency(self):
        marks = sig.aggregate_marks(["1:00 すき", "1:00 わかる", "2:00 これ"])
        assert marks[0] == {"seconds": 60, "count": 2,
                            "samples": ["1:00 すき", "1:00 わかる"]}
        assert marks[1]["seconds"] == 120

    def test_ties_break_by_earlier_second(self):
        marks = sig.aggregate_marks(["2:00 a", "1:00 b"])
        assert [m["seconds"] for m in marks] == [60, 120]

    def test_samples_are_capped(self):
        marks = sig.aggregate_marks([f"1:00 c{i}" for i in range(10)])
        assert marks[0]["count"] == 10
        assert len(marks[0]["samples"]) == sig.SAMPLE_LIMIT


class TestParseAstats:
    def test_bins_by_second(self):
        text = "\n".join([
            "frame:0 pts_time:0.1",
            "lavfi.astats.Overall.RMS_level=-20.0",
            "frame:1 pts_time:0.9",
            "lavfi.astats.Overall.RMS_level=-30.0",
            "frame:2 pts_time:1.5",
            "lavfi.astats.Overall.RMS_level=-10.0",
        ])
        assert sig.parse_astats(text) == [{"t": 0.0, "db": -25.0}, {"t": 1.0, "db": -10.0}]

    def test_drops_silence(self):
        text = ("frame:0 pts_time:0.0\nlavfi.astats.Overall.RMS_level=-inf\n"
                "frame:1 pts_time:1.0\nlavfi.astats.Overall.RMS_level=-12.0")
        assert sig.parse_astats(text) == [{"t": 1.0, "db": -12.0}]

    def test_empty(self):
        assert sig.parse_astats("") == []


class TestLoudnessScores:
    def test_empty(self):
        assert sig.loudness_scores([]) == []

    def test_flat_signal_scores_zero(self):
        env = [{"t": float(i), "db": -20.0} for i in range(10)]
        assert all(s["score"] == 0.0 for s in sig.loudness_scores(env))

    def test_spike_reaches_one(self):
        env = [{"t": float(i), "db": -20.0} for i in range(20)]
        env[10]["db"] = -5.0
        scores = sig.loudness_scores(env)
        assert scores[10]["score"] == 1.0
        assert scores[0]["score"] == 0.0

    def test_absolute_level_does_not_matter(self):
        """全体が大きい動画でも小さい動画でも同じ尺度になること。"""
        quiet = [{"t": float(i), "db": -40.0} for i in range(20)]
        loud = [{"t": float(i), "db": -10.0} for i in range(20)]
        quiet[10]["db"] = -25.0
        loud[10]["db"] = 5.0
        assert (sig.loudness_scores(quiet)[10]["score"]
                == sig.loudness_scores(loud)[10]["score"] == 1.0)


class TestLexicalMarks:
    def test_picks_up_sound_tags(self):
        segs = [{"start": 10.0, "end": 11.0, "text": "[笑い]"},
                {"start": 20.0, "end": 21.0, "text": "[大歓声]"}]
        marks = sig.lexical_marks(segs)
        assert {m["kind"] for m in marks} == {"笑い", "歓声"}

    def test_picks_up_reaction_words(self):
        segs = [{"start": 5.0, "end": 6.0, "text": "え、マジで?どういうこと?"}]
        marks = sig.lexical_marks(segs)
        assert marks and marks[0]["kind"] == "驚き"
        assert marks[0]["seconds"] == 5

    def test_one_hit_per_kind_per_line(self):
        segs = [{"start": 0.0, "end": 1.0, "text": "マジやばい嘘だろ"}]
        assert len(sig.lexical_marks(segs)) == 1

    def test_a_line_can_hit_multiple_kinds(self):
        segs = [{"start": 0.0, "end": 1.0, "text": "お前マジかよ[笑い]"}]
        kinds = {m["kind"] for m in sig.lexical_marks(segs)}
        assert kinds == {"いじり", "驚き", "笑い"}

    def test_no_match(self):
        assert sig.lexical_marks([{"start": 0.0, "end": 1.0, "text": "そうですね"}]) == []
