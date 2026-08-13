# -*- coding: utf-8 -*-
import pytest

from clipper import metadata, upload


@pytest.fixture
def entry():
    return {"video_id": "vid1",
            "meta": {"title": "【魔神】催眠術かけてみた", "description": ""},
            "clips": [{"clip_id": "auto01", "start": 1060.0, "end": 1117.0}]}


@pytest.fixture
def clip(entry):
    return entry["clips"][0]


class TestTitleValidation:
    def test_accepts_a_normal_title(self):
        metadata.validate_title("催眠術で本当に声が出なくなった瞬間【コムドット切り抜き】")

    def test_rejects_empty(self):
        with pytest.raises(metadata.InvalidTitle):
            metadata.validate_title("   ")

    def test_rejects_too_long(self):
        with pytest.raises(metadata.InvalidTitle):
            metadata.validate_title("あ" * 101 + "切り抜き")

    @pytest.mark.parametrize("word", ["公式", "公認", "オフィシャル", "コラボ"])
    def test_rejects_words_that_imply_affiliation(self, word):
        """権利者との関係は黙認。提携しているかのような表記は事実に反する。"""
        with pytest.raises(metadata.InvalidTitle):
            metadata.validate_title(f"コムドット{word}切り抜き")

    def test_requires_the_word_kirinuki(self):
        with pytest.raises(metadata.InvalidTitle):
            metadata.validate_title("催眠術で声が出なくなった瞬間")


class TestDescription:
    def test_always_links_the_source_at_the_timestamp(self, entry, clip):
        d = metadata.build_description(entry, clip)
        assert "https://www.youtube.com/watch?v=vid1&t=1060s" in d

    def test_always_states_it_is_unaffiliated(self, entry, clip):
        d = metadata.build_description(entry, clip)
        assert "関係がありません" in d
        assert metadata.OFFICIAL_URL in d

    def test_always_offers_takedown_contact(self, entry, clip):
        assert "削除・修正" in metadata.build_description(entry, clip)

    def test_shorts_get_the_hashtag(self, entry, clip):
        assert "#Shorts" in metadata.build_description(entry, clip, is_short=True)
        assert "#Shorts" not in metadata.build_description(entry, clip, is_short=False)

    def test_fits_the_api_limit(self, entry, clip):
        assert len(metadata.build_description(entry, clip)) <= metadata.DESCRIPTION_MAX


class TestBuildBody:
    def test_declares_japanese(self, entry, clip):
        body = metadata.build_body(entry, clip, "テスト切り抜き")
        assert body["defaultLanguage"] == "ja"
        assert body["defaultAudioLanguage"] == "ja"

    def test_rejects_a_bad_title_before_touching_the_api(self, entry, clip):
        with pytest.raises(metadata.InvalidTitle):
            metadata.build_body(entry, clip, "コムドット公式切り抜き")


class TestPublishIsGated:
    """非公開アップロードと公開は別物。公開だけがゲートを要る。"""

    def test_publish_refuses_while_permission_is_pending(self, entry, monkeypatch):
        entry["clips"][0]["upload"] = {"youtube_video_id": "yt1"}
        monkeypatch.setattr(upload, "find_clip",
                            lambda v, c: (entry, entry["clips"][0]))
        monkeypatch.setattr(upload.gate, "evaluate", lambda *a, **k: {
            "result": "held", "reasons": ["許諾ステータスが pending（granted ではない）"]})
        with pytest.raises(upload.UploadBlocked, match="ゲートを通っていない"):
            upload.publish("vid1", "auto01", service=object())

    def test_publish_refuses_when_not_uploaded_yet(self, entry, monkeypatch):
        monkeypatch.setattr(upload, "find_clip",
                            lambda v, c: (entry, entry["clips"][0]))
        with pytest.raises(upload.UploadBlocked, match="まだアップロードされていません"):
            upload.publish("vid1", "auto01", service=object())


class TestChannelGuard:
    def test_refuses_without_an_expected_channel_id(self, monkeypatch):
        monkeypatch.setattr(upload.config, "settings", lambda: {"channel": {}})
        with pytest.raises(upload.UploadBlocked, match="expected_channel_id"):
            upload.assert_expected_channel(object())

    def test_refuses_on_mismatch(self, monkeypatch):
        monkeypatch.setattr(upload.config, "settings",
                            lambda: {"channel": {"expected_channel_id": "UC_want"}})
        monkeypatch.setattr(upload, "current_channel",
                            lambda s: {"id": "UC_other", "title": "別チャンネル"})
        with pytest.raises(upload.UploadBlocked, match="一致しません"):
            upload.assert_expected_channel(object())

    def test_passes_on_match(self, monkeypatch):
        monkeypatch.setattr(upload.config, "settings",
                            lambda: {"channel": {"expected_channel_id": "UC_want"}})
        monkeypatch.setattr(upload, "current_channel",
                            lambda s: {"id": "UC_want", "title": "名場面ch"})
        assert upload.assert_expected_channel(object())["id"] == "UC_want"
