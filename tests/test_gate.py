# -*- coding: utf-8 -*-
import pytest

from clipper import gate


@pytest.fixture
def entry():
    return {"video_id": "vid1", "meta": {"title": "ふつうの回", "description": "本文"},
            "clips": []}


@pytest.fixture
def clip():
    return {"clip_id": "clip01", "start": 100.0, "end": 160.0}


@pytest.fixture
def runtime():
    return {"kill_switch": False, "kill_reason": None, "published": {}}


@pytest.fixture
def granted(monkeypatch):
    """許諾が下りている状態にする。他の条件を単体で見るため。"""
    monkeypatch.setattr(gate.config, "permission", lambda: {"status": "granted"})


@pytest.fixture
def pending(monkeypatch):
    """許諾の回答待ちの状態にする。

    **実物の config/permission.yaml を読ませない。** 2026-09-02 に status を
    granted へ変えたところ、それを pending 前提で書いていたテストが落ちた。
    ゲートの挙動を固定したいのであって、設定ファイルの現在値ではない。
    """
    monkeypatch.setattr(gate.config, "permission", lambda: {"status": "pending"})


@pytest.fixture
def no_exclusions(monkeypatch):
    monkeypatch.setattr(gate.config, "exclusions", lambda: {
        "video_ids": [], "title_patterns": [], "description_patterns": [],
        "blocked_terms": []})


def test_pending_permission_blocks_everything(entry, clip, runtime, pending,
                                              no_exclusions):
    """pending の間は1本も出ないことを固定する。"""
    got = gate.evaluate(entry, clip, runtime=runtime)
    assert got["result"] == "held"
    assert any("許諾ステータス" in r for r in got["reasons"])


def test_passes_when_everything_is_clear(entry, clip, runtime, granted, no_exclusions):
    assert gate.evaluate(entry, clip, runtime=runtime) == {"result": "pass", "reasons": []}


def test_collects_every_reason_not_just_the_first(entry, clip, runtime, pending,
                                                 monkeypatch):
    monkeypatch.setattr(gate.config, "exclusions", lambda: {
        "video_ids": ["vid1"], "title_patterns": ["ふつう"],
        "description_patterns": [], "blocked_terms": []})
    got = gate.evaluate(entry, clip, runtime=runtime)
    assert len(got["reasons"]) >= 3          # 許諾 + video_ids + タイトル


def test_denied_permission_blocks_everything(entry, clip, runtime, no_exclusions,
                                             monkeypatch):
    """granted 以外は全部止める。denied も pending と同じ扱い。"""
    monkeypatch.setattr(gate.config, "permission", lambda: {"status": "denied"})
    got = gate.evaluate(entry, clip, runtime=runtime)
    assert got["result"] == "held"
    assert any("許諾ステータス" in r for r in got["reasons"])


def test_excluded_video_id(entry, clip, runtime, granted, monkeypatch):
    monkeypatch.setattr(gate.config, "exclusions", lambda: {
        "video_ids": ["vid1"], "title_patterns": [], "description_patterns": [],
        "blocked_terms": []})
    assert gate.evaluate(entry, clip, runtime=runtime)["result"] == "held"


def test_sponsored_video_is_held_by_description(entry, clip, runtime, granted, monkeypatch):
    entry["meta"]["description"] = "本日の動画は提供でお送りします"
    monkeypatch.setattr(gate.config, "exclusions", lambda: {
        "video_ids": [], "title_patterns": [], "description_patterns": ["提供"],
        "blocked_terms": []})
    got = gate.evaluate(entry, clip, runtime=runtime)
    assert got["result"] == "held"
    assert any("提供" in r for r in got["reasons"])


def test_blocked_term_inside_the_clip_only(entry, clip, runtime, granted, monkeypatch):
    monkeypatch.setattr(gate.config, "exclusions", lambda: {
        "video_ids": [], "title_patterns": [], "description_patterns": [],
        "blocked_terms": ["炎上"]})
    inside = [{"start": 120.0, "end": 121.0, "text": "あれは炎上したよね"}]
    outside = [{"start": 900.0, "end": 901.0, "text": "あれは炎上したよね"}]
    assert gate.evaluate(entry, clip, inside, runtime=runtime)["result"] == "held"
    assert gate.evaluate(entry, clip, outside, runtime=runtime)["result"] == "pass"


def test_duplicate_clip_is_held(entry, clip, runtime, granted, no_exclusions):
    runtime["published"]["2026-08-01"] = ["vid1/clip01"]
    got = gate.evaluate(entry, clip, runtime=runtime, today="2026-08-14")
    assert any("既に投稿" in r for r in got["reasons"])


def test_daily_limit(entry, clip, runtime, granted, no_exclusions, monkeypatch):
    monkeypatch.setattr(gate.config, "settings",
                        lambda: {"limits": {"max_publish_per_day": 2}})
    runtime["published"]["2026-08-14"] = ["vid9/a", "vid9/b"]
    got = gate.evaluate(entry, clip, runtime=runtime, today="2026-08-14")
    assert any("上限" in r for r in got["reasons"])


def test_limit_is_per_day(entry, clip, runtime, granted, no_exclusions, monkeypatch):
    monkeypatch.setattr(gate.config, "settings",
                        lambda: {"limits": {"max_publish_per_day": 2}})
    runtime["published"]["2026-08-13"] = ["vid9/a", "vid9/b"]
    assert gate.evaluate(entry, clip, runtime=runtime,
                         today="2026-08-14")["result"] == "pass"


def test_kill_switch_stops_everything(entry, clip, runtime, granted, no_exclusions):
    runtime["kill_switch"] = True
    runtime["kill_reason"] = "著作権の申し立てを検知"
    got = gate.evaluate(entry, clip, runtime=runtime)
    assert got["result"] == "held"
    assert any("キルスイッチ" in r for r in got["reasons"])


# --- 収益化の許諾条件 ---------------------------------------------------
#
# permission.yaml は「conditions を gate が読んで判定する」と書いてあったが、
# 実際には status しか見ておらず conditions は誰も読んでいなかった。
# 収益化してよいかの回答が取れていないまま収益化すると、許諾の範囲を
# 超える。人が気づいて止めるのではなく、ここで機械的に止める。


@pytest.fixture
def not_monetized(monkeypatch):
    monkeypatch.setattr(gate.config, "settings", lambda: {
        "limits": {"max_publish_per_day": 2},
        "channel": {"monetization_enabled": False}})


def _monetized(monkeypatch):
    monkeypatch.setattr(gate.config, "settings", lambda: {
        "limits": {"max_publish_per_day": 2},
        "channel": {"monetization_enabled": True}})


def _perm(monkeypatch, monetization):
    monkeypatch.setattr(gate.config, "permission", lambda: {
        "status": "granted", "conditions": {"monetization": monetization}})


def test_monetized_channel_is_held_while_monetization_is_unknown(
        entry, clip, runtime, no_exclusions, monkeypatch):
    """収益化してよいかの回答が無いまま収益化していたら止める。"""
    _monetized(monkeypatch)
    _perm(monkeypatch, "unknown")
    got = gate.evaluate(entry, clip, runtime=runtime)
    assert got["result"] == "held"
    assert any("収益化" in r for r in got["reasons"])


def test_monetized_channel_is_held_when_monetization_is_not_allowed(
        entry, clip, runtime, no_exclusions, monkeypatch):
    _monetized(monkeypatch)
    _perm(monkeypatch, "not_allowed")
    got = gate.evaluate(entry, clip, runtime=runtime)
    assert got["result"] == "held"
    assert any("収益化" in r for r in got["reasons"])


def test_monetized_channel_passes_when_monetization_is_allowed(
        entry, clip, runtime, no_exclusions, monkeypatch):
    _monetized(monkeypatch)
    _perm(monkeypatch, "allowed")
    assert gate.evaluate(entry, clip, runtime=runtime)["result"] == "pass"


def test_unmonetized_channel_passes_even_when_monetization_is_unknown(
        entry, clip, runtime, no_exclusions, not_monetized, monkeypatch):
    """収益化していないうちは、条件が未確認でも投稿は止めない。

    止めるべきは「許諾の範囲を超えて収益を得ること」であって、投稿そのもの
    ではない。ここで全部止めると在庫が動かなくなるだけで安全にはならない。
    """
    _perm(monkeypatch, "unknown")
    assert gate.evaluate(entry, clip, runtime=runtime)["result"] == "pass"


def test_missing_channel_settings_are_treated_as_not_monetized(
        entry, clip, runtime, granted, no_exclusions, monkeypatch):
    """settings.yaml に channel が無くても落ちない。"""
    monkeypatch.setattr(gate.config, "settings",
                        lambda: {"limits": {"max_publish_per_day": 2}})
    assert gate.evaluate(entry, clip, runtime=runtime)["result"] == "pass"
