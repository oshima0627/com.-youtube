# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw

from clipper import overlay


def _draw():
    return ImageDraw.Draw(Image.new("RGBA", (1080, 1920)))


class TestWrap:
    def test_short_text_stays_on_one_line(self):
        d = _draw()
        assert overlay.wrap(d, "催眠術の企画", overlay.font(78), 900) == ["催眠術の企画"]

    def test_wraps_japanese_without_spaces(self):
        d = _draw()
        f = overlay.font(78)
        lines = overlay.wrap(d, "あ" * 40, f, 900)
        assert len(lines) > 1
        assert all(d.textlength(x, font=f) <= 900 for x in lines)

    def test_respects_explicit_newlines(self):
        d = _draw()
        assert overlay.wrap(d, "上の行\n下の行", overlay.font(46), 900) == ["上の行", "下の行"]

    def test_empty(self):
        assert overlay.wrap(_draw(), "", overlay.font(46), 900) == []


class TestBreaksAtSentenceEnd:
    def test_always_breaks_after_a_period(self):
        """句点では必ず改行する。1行に収まる場合でも分ける。"""
        d = _draw()
        lines = overlay.wrap(d, "一文目。二文目。", overlay.font(46), 2000)
        assert lines == ["一文目。", "二文目。"]

    def test_question_and_exclamation_too(self):
        d = _draw()
        assert overlay.wrap(d, "本当？そうなる！", overlay.font(46), 2000) == \
            ["本当？", "そうなる！"]


class TestBreaksAtReadablePlaces:
    def _lines(self, text, size=78, width=900):
        return overlay.wrap(_draw(), text, overlay.font(size), width)

    def test_prefers_breaking_after_a_comma(self):
        # 読点が1行目に収まる範囲にあるときは、そこで折る
        lines = self._lines("企画で、被験者は本人が選んだ")
        assert lines[0].endswith("、"), lines

    def test_falls_back_when_the_comma_is_out_of_reach(self):
        """読点が1行目の幅を超えた先にある場合は、届く範囲で最良の位置を選ぶ。
        語の途中では割らない。"""
        lines = self._lines("プロの催眠術師を事務所に招いた企画で、被験者は本人が選んだ")
        assert len(lines) > 1
        assert lines[0][-1] not in overlay.FORBID_LINE_END
        assert lines[1][0] not in overlay.FORBID_LINE_START

    def test_prefers_breaking_after_a_particle(self):
        lines = self._lines("カメラにアピールしたくてたまらなくなる暗示をかけられた")
        assert lines[0][-1] in "はがをにへとでもやのりてえ" or lines[0].endswith("、")

    def test_breaks_after_the_te_form_not_inside_the_word(self):
        """実際にサムネイルで「たまらな／くなる」と割れた回帰。"""
        lines = self._lines("カメラにアピールしたくてたまらなくなる暗示",
                            size=72, width=1170)
        assert len(lines) == 2
        assert lines[0].endswith("て"), lines
        assert lines[1] == "たまらなくなる暗示", lines

    def test_prefers_a_script_boundary_over_the_middle_of_a_word(self):
        """助詞が届かないときは文字種の変わり目で折る。"""
        lines = self._lines("ドッキリ大成功おめでとうございました", size=78, width=700)
        for a, b in zip(lines, lines[1:]):
            assert overlay._break_score(a + b, len(a)) > 1, lines

    def test_does_not_orphan_one_character(self):
        """「〜下が / る」のように最終行へ1文字だけ落とさない。"""
        for text in ("小さい音にビビりすぎて後ろに下がる",
                     "ネギトロ巻きを完璧に言い当てて本人たちが驚愕する"):
            lines = self._lines(text)
            if len(lines) > 1:
                assert len(lines[-1]) > overlay.ORPHAN_MAX, (text, lines)


class TestKinsoku:
    def _lines(self, text, width=900):
        return overlay.wrap(_draw(), text, overlay.font(78), width)

    def test_no_line_starts_with_punctuation(self):
        text = "術者いわく、かかるかどうかは本人が楽しめているかで決まる、らしい"
        for line in self._lines(text):
            assert line[0] not in overlay.FORBID_LINE_START, line

    def test_no_line_starts_with_a_small_kana(self):
        text = "ちょっとだけ声が出にくくなってしまったっていう話をしていた"
        for line in self._lines(text):
            assert line[0] not in "ぁぃぅぇぉっゃゅょーァィゥェォッャュョ", line

    def test_no_line_ends_with_an_opening_bracket(self):
        text = "術者が「普段できない自分を楽しむ」という暗示をかけた直後の場面"
        for line in self._lines(text):
            assert line[-1] not in overlay.FORBID_LINE_END, line

    def test_still_fits_the_width(self):
        d = _draw()
        f = overlay.font(78)
        text = "プロの催眠術師を事務所に招いた企画。術者いわく、かかるかどうかは本人が楽しめているかで決まる"
        for line in overlay.wrap(d, text, f, 900):
            assert d.textlength(line, font=f) <= 900, line


class TestBuild:
    def test_writes_a_transparent_png_of_the_right_size(self, tmp_path):
        p = overlay.build("見出し", "補足", tmp_path / "o.png")
        with Image.open(p) as im:
            assert im.size == (1080, 1920)
            assert im.mode == "RGBA"

    def test_leaves_the_video_band_untouched(self, tmp_path):
        """映像が乗る中央帯には何も描かない。かぶせると本編が読めなくなる。"""
        p = overlay.build("見出し" * 6, "補足" * 30, tmp_path / "o.png")
        with Image.open(p) as im:
            video_h = int(1080 * 9 / 16)
            top = (1920 - video_h) // 2
            band = im.crop((0, top, 1080, top + video_h))
            assert band.getbbox() is None          # 完全に透明

    @staticmethod
    def _has_text(im, box):
        """明るい画素があるか。暗いスクリムだけの帯と、文字がある帯を区別する。"""
        region = im.crop(box).convert("RGB")
        return max(region.getdata(), key=lambda p: sum(p))[0] > 180

    def test_hook_goes_to_the_top_zone_only(self, tmp_path):
        p = overlay.build("見出し", None, tmp_path / "o.png", handle=None)
        with Image.open(p) as im:
            top = (1920 - int(1080 * 9 / 16)) // 2
            assert self._has_text(im, (0, 0, 1080, top))
            assert not self._has_text(im, (0, top + int(1080 * 9 / 16), 1080, 1920))

    def test_footer_goes_to_the_bottom_zone_only(self, tmp_path):
        p = overlay.build(None, "補足", tmp_path / "o.png", handle=None)
        with Image.open(p) as im:
            top = (1920 - int(1080 * 9 / 16)) // 2
            assert self._has_text(im, (0, top + int(1080 * 9 / 16), 1080, 1920))
            assert not self._has_text(im, (0, 0, 1080, top))

    def test_scrim_covers_both_dead_zones(self, tmp_path):
        """元動画の焼き込み字幕のぼけを沈めるため、帯は両方とも暗く覆う。"""
        p = overlay.build("見出し", None, tmp_path / "o.png")
        with Image.open(p) as im:
            bottom = (1920 - int(1080 * 9 / 16)) // 2 + int(1080 * 9 / 16)
            assert im.crop((0, bottom + 200, 1080, 1900)).getbbox() is not None

    def test_nothing_drawn_when_both_empty(self, tmp_path):
        p = overlay.build(None, None, tmp_path / "o.png")
        with Image.open(p) as im:
            assert im.getbbox() is None
