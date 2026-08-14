# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw

from clipper import overlay, thumbnail


def _draw():
    return ImageDraw.Draw(Image.new("RGB", (thumbnail.WIDTH, thumbnail.HEIGHT)))


class TestFitLines:
    def test_uses_the_same_break_positions_as_the_video(self):
        """サムネイルは動画より広いが、割れ方は揃える。
        同じ見出しなのに違う位置で折れると別物に見える。"""
        d = _draw()
        for hook in ("「喋れない」と言われて本当に声が出なくなる",
                     "小さい音にビビりすぎて後ろに下がる",
                     "カメラにアピールしたくてたまらなくなる暗示"):
            video = overlay.wrap(d, hook, overlay.font(78), overlay.TEXT_MAX_WIDTH)
            thumb, _ = thumbnail.fit_lines(d, hook, thumbnail.WIDTH - 110)
            assert thumb == video, hook

    def test_shrinks_the_font_until_it_fits(self):
        d = _draw()
        lines, f = thumbnail.fit_lines(d, "あ" * 30, 600)
        assert max(d.textlength(x, font=f) for x in lines) <= 600 or f.size == thumbnail.MIN_SIZE

    def test_keeps_the_base_size_when_it_already_fits(self):
        d = _draw()
        _, f = thumbnail.fit_lines(d, "短い見出し", thumbnail.WIDTH - 110)
        assert f.size == thumbnail.BASE_SIZE

    def test_never_goes_below_the_floor(self):
        d = _draw()
        _, f = thumbnail.fit_lines(d, "あ" * 60, 100)
        assert f.size >= thumbnail.MIN_SIZE


class TestCompose:
    def test_writes_a_thumbnail_of_the_right_size(self, tmp_path):
        frame = tmp_path / "f.png"
        Image.new("RGB", (thumbnail.WIDTH, thumbnail.HEIGHT), (80, 80, 90)).save(frame)
        out = thumbnail.compose(frame, "見出し", tmp_path / "t.png")
        with Image.open(out) as im:
            assert im.size == (thumbnail.WIDTH, thumbnail.HEIGHT)

    def test_band_is_opaque(self, tmp_path):
        """半透明にすると元動画の焼き込みテロップが透けて両方読めなくなる。"""
        frame = tmp_path / "f.png"
        Image.new("RGB", (thumbnail.WIDTH, thumbnail.HEIGHT), (255, 40, 40)).save(frame)
        out = thumbnail.compose(frame, "見出し", tmp_path / "t.png")
        with Image.open(out) as im:
            # 帯の中で文字に当たらない左下の隅を見る
            assert im.getpixel((12, thumbnail.HEIGHT - 12)) == (0, 0, 0)

    def test_without_a_hook_the_frame_passes_through(self, tmp_path):
        frame = tmp_path / "f.png"
        Image.new("RGB", (thumbnail.WIDTH, thumbnail.HEIGHT), (10, 200, 30)).save(frame)
        out = thumbnail.compose(frame, None, tmp_path / "t.png")
        with Image.open(out) as im:
            assert im.getpixel((12, thumbnail.HEIGHT - 12)) == (10, 200, 30)
