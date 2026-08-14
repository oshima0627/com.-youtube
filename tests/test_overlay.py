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
