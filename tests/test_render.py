# -*- coding: utf-8 -*-
import pytest
from PIL import Image

from clipper import overlay, render


class TestLengthLimit:
    """電話番号確認ができないため15分超は投稿できない。書き出す前に止める。"""

    def test_accepts_a_normal_long_form_length(self):
        assert render.assert_within_limit(780) == 780

    def test_accepts_just_under_the_wall(self):
        assert render.assert_within_limit(899) == 899

    def test_rejects_exactly_fifteen_minutes(self):
        with pytest.raises(render.TooLong):
            render.assert_within_limit(900)

    def test_rejects_longer(self):
        with pytest.raises(render.TooLong):
            render.assert_within_limit(1200)

    def test_message_points_at_the_cause(self):
        with pytest.raises(render.TooLong, match="電話番号確認"):
            render.assert_within_limit(1000)


class TestWideOverlay:
    def test_is_the_right_size(self, tmp_path):
        p = overlay.build_wide("見出し", "補足", tmp_path / "w.png")
        with Image.open(p) as im:
            assert im.size == (1920, 1080)

    def test_stays_in_the_upper_area(self, tmp_path):
        """下部には置かない。本編が画面下に字幕を焼き込んでいるため必ずぶつかる。"""
        p = overlay.build_wide("見出し" * 4, "補足" * 20, tmp_path / "w.png")
        with Image.open(p) as im:
            lower = im.crop((0, 540, 1920, 1080))
            assert lower.getbbox() is None

    def test_nothing_drawn_without_a_hook(self, tmp_path):
        p = overlay.build_wide(None, "補足だけ", tmp_path / "w.png")
        with Image.open(p) as im:
            assert im.getbbox() is None

    def test_uses_the_same_wrapping_rules(self, tmp_path):
        """改行位置の基準はショートと共通。同じ関数を通す。"""
        from PIL import ImageDraw
        d = ImageDraw.Draw(Image.new("RGBA", (1920, 1080)))
        lines = overlay.wrap(d, "「喋れない」と言われて本当に声が出なくなる",
                             overlay.font(78), overlay.TEXT_MAX_WIDTH)
        assert lines == ["「喋れない」と言われて", "本当に声が出なくなる"]
