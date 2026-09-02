# -*- coding: utf-8 -*-
"""ショートのタイトルの型。

2026-09-02 の実測（docs/analytics-2026-09-02.md）で、公開済み13本が
docs/market-scan.md に書いてある型を満たしていないことが分かった。

    メンバー名を含む   競合 22/27  →  自分 2/13
    #shorts を含む     競合 46/120 →  自分 0/13

型は docs に書いてあるだけで、コードのどこからも強制されていなかった
（`short_title()` は定義されていたが呼び出し元が無い）。ここで機械の検査にする。
"""

import pytest

from clipper import metadata


class TestShortTitle:
    def test_puts_the_base_tags_in_the_title(self):
        t = metadata.short_title("催眠術で本当に喋れなくなるのがヤバすぎる", ["ひゅうが"])
        assert "#コムドット" in t
        assert "#コムドット切り抜き" in t

    def test_puts_shorts_tag_in_the_title(self):
        t = metadata.short_title("催眠術で本当に喋れなくなるのがヤバすぎる", ["ひゅうが"])
        assert "#shorts" in t

    def test_puts_each_member_in_the_title(self):
        t = metadata.short_title("2人の作戦会議が主導権争いになる", ["やまと", "ゆうた"])
        assert "#やまと" in t
        assert "#ゆうた" in t

    def test_keeps_the_body_at_the_head(self):
        t = metadata.short_title("黒ひげにビビりすぎるのが最高", ["あむぎり"])
        assert t.startswith("黒ひげにビビりすぎるのが最高 #")

    def test_rejects_a_name_that_is_not_a_member(self):
        """自動字幕は固有名詞を崩す。名簿に無い名前をタグにしない。"""
        with pytest.raises(metadata.InvalidTitle):
            metadata.short_title("催眠術がヤバすぎる", ["スプリンガー母"])

    def test_never_cuts_a_hashtag_in_half(self):
        t = metadata.short_title("あ" * 60, ["やまと", "ゆうた", "ゆうま"])
        assert len(t) <= metadata.TITLE_MAX
        for tag in t.split()[1:]:
            assert tag.startswith("#")
        assert "#コムドット切り抜き" in t
        assert "#shorts" in t

    def test_checks_what_it_built(self):
        """組み立てたものが検査を通らないなら、その場で落とす。"""
        with pytest.raises(metadata.InvalidTitle):
            metadata.short_title("公式の場面が最高すぎる", ["やまと"])
        with pytest.raises(metadata.InvalidTitle):
            metadata.short_title("誰が映っているか分からない場面")

    def test_refuses_a_body_that_leaves_no_room_for_the_base_tags(self):
        with pytest.raises(metadata.InvalidTitle):
            metadata.short_title("あ" * 90, ["やまと"])


class TestShortTitleValidation:
    def test_accepts_a_title_built_by_short_title(self):
        t = metadata.short_title("催眠術で本当に喋れなくなるのがヤバすぎる", ["ひゅうが"])
        metadata.validate_title(t, is_short=True)

    def test_rejects_a_short_without_the_shorts_tag(self):
        with pytest.raises(metadata.InvalidTitle):
            metadata.validate_title(
                "催眠術で喋れなくなる #コムドット #コムドット切り抜き #ひゅうが",
                is_short=True)

    def test_rejects_a_short_without_a_member(self):
        with pytest.raises(metadata.InvalidTitle):
            metadata.validate_title(
                "催眠術で喋れなくなる #コムドット #コムドット切り抜き #shorts",
                is_short=True)

    def test_accepts_a_member_named_in_the_body_instead_of_a_tag(self):
        """本文で名指ししているものを、タグが無いだけで弾かない。"""
        metadata.validate_title(
            "ひゅうがが催眠術で喋れなくなる #コムドット #コムドット切り抜き #shorts",
            is_short=True)

    def test_does_not_impose_the_shorts_rules_on_wide(self):
        metadata.validate_title("極悪の食事を1本まるごと【コムドット切り抜き】")

    def test_still_rejects_words_that_imply_affiliation(self):
        with pytest.raises(metadata.InvalidTitle):
            metadata.validate_title(
                "公式のやまと #コムドット #コムドット切り抜き #shorts", is_short=True)


class TestBuildBody:
    def test_a_short_gets_the_shorts_rules(self):
        entry = {"video_id": "vid1", "meta": {"title": "元動画", "description": ""}}
        clip = {"clip_id": "auto01", "start": 10.0, "end": 70.0}
        with pytest.raises(metadata.InvalidTitle):
            metadata.build_body(entry, clip,
                                "催眠術で喋れなくなる #コムドット #コムドット切り抜き",
                                is_short=True)
