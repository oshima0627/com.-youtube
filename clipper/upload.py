# -*- coding: utf-8 -*-
"""YouTube へのアップロード。

  python -m clipper auth                        初回の認証だけ通す
  python -m clipper upload <video_id> <clip_id> 非公開でアップロード

**非公開アップロードと公開は別の操作として分けてある。**
非公開は誰にも見えないので、許諾の回答を待つ間に在庫を作っておける。
公開（`publish`）だけが gate の判定を必要とする。

API キーではアップロードできない。videos.insert は OAuth 2.0 の
アクセストークン（youtube.upload スコープ）を要求する。
"""

import json
import sys

from . import config, gate, ledger, metadata

CLIENT_SECRET = config.ROOT / "client_secret.json"
TOKEN = config.ROOT / "token.json"

# videos.insert → youtube.upload
# channels.list → youtube.readonly（アップロード先チャンネルの事前確認に要る）
# videos.update → youtube.force-ssl（公開設定の変更。これより狭いスコープが無い）
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class UploadBlocked(RuntimeError):
    """上げてはいけない状態。握りつぶさずに止める。"""


def get_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise UploadBlocked(
            "依存が足りません: "
            "pip install google-api-python-client google-auth-oauthlib")

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:                                  # noqa: BLE001
            # OAuth 同意画面が「テスト中」のままだとリフレッシュトークンが
            # 7日で失効する。無人運転の途中でここに落ちるので、症状と対処を出す
            if "invalid_grant" in str(e):
                raise UploadBlocked(
                    "リフレッシュトークンが失効しています（invalid_grant）。\n"
                    "  OAuth 同意画面が「テスト中」だと7日で失効します。\n"
                    f"  {TOKEN.name} を削除し、python -m clipper auth をやり直してください。\n"
                    "  詳細は docs/youtube-api-setup.md。")
            raise
    if not creds or not creds.valid:
        if not CLIENT_SECRET.exists():
            raise UploadBlocked(
                f"{CLIENT_SECRET.name} がありません。\n"
                "  Google Cloud で YouTube Data API v3 を有効化し、\n"
                "  OAuth クライアント（デスクトップアプリ）を作って直下に置いてください。")
        # 初回だけブラウザの同意画面が開く。以降は refresh_token で無人化される
        creds = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET), SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        print(f"認証情報を保存しました: {TOKEN.name}（.gitignore 済み）")

    return build("youtube", "v3", credentials=creds)


def _raise_if_quota(e):
    """クォータ超過を UploadBlocked に翻訳する。

    既定は 10,000ユニット/日で、videos.insert が1,600と重い。超過すると
    channels.list の1ユニットすら通らず、状態の確認すらできなくなる。
    回復は太平洋時間の0時（JSTの16〜17時）で、日本時間の日付が変わっても戻らない。

    **OAuth クライアントを他プロジェクトと共有しているとクォータも共有される。**
    切り離すには別の Google Cloud プロジェクトで OAuth クライアントを作り直す。
    """
    text = str(e)
    if "quotaExceeded" in text or "exceeded your" in text:
        raise UploadBlocked(
            "YouTube Data API の1日あたりクォータを超過しています。\n"
            "  回復は太平洋時間の0時（JSTの16〜17時ごろ）。日付が変わっても戻りません。\n"
            "  このクライアントを他プロジェクトと共有している場合、"
            "クォータも共有されます。")
    # クォータ以外は呼び出し元に判断を委ねる。ここで再送出すると
    # 「サムネイル失敗でも動画は残す」といった扱いができなくなる


def current_channel(service):
    """いま認証しているトークンがどのチャンネルに紐づくかを返す。"""
    from googleapiclient.errors import HttpError
    try:
        items = service.channels().list(
            part="snippet", mine=True).execute().get("items", [])
    except HttpError as e:
        _raise_if_quota(e)
    if not items:
        return None
    return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]}


def assert_expected_channel(service):
    """settings.yaml の expected_channel_id と一致しない限り上げない。

    同じ Google アカウントに複数チャンネルがあると、同意画面でアカウントを
    選んだだけでは足りず、API は既定チャンネルに上げる。取り違えたら消して
    上げ直すことになるので、上げる前に止めるほうが安い。
    """
    expected = (config.settings().get("channel") or {}).get("expected_channel_id")
    if not expected:
        raise UploadBlocked(
            "settings.yaml に channel.expected_channel_id がありません。\n"
            "  取り違えを防げないのでアップロードしません。\n"
            "  `python -m clipper auth` で表示されるチャンネルIDを書いてください。")
    ch = current_channel(service)
    if ch is None or ch["id"] != expected:
        got = f"{ch['title']}（{ch['id']}）" if ch else "取得できず"
        raise UploadBlocked(
            "アップロード先のチャンネルが指定と一致しません。\n"
            f"  期待: {expected}\n"
            f"  実際: {got}\n"
            f"  {TOKEN.name} を消し、同意画面で正しいチャンネルを選び直してください。")
    return ch


def output_path(video_id, clip):
    """書き出し済みファイルを探す。ショートと横型で接尾辞が違う。"""
    out = config.out_dir()
    for suffix in ("short", "wide"):
        p = out / f"{video_id}_{clip['clip_id']}_{suffix}.mp4"
        if p.exists():
            return p
    raise UploadBlocked(
        f"{out / f'{video_id}_{clip['clip_id']}_*.mp4'} がありません。"
        "先に書き出してください")


def is_short(path):
    """ショートかどうか。#Shorts タグの要否とサムネイルの扱いが変わる。"""
    return path.name.endswith("_short.mp4")


def clip_is_short(clip):
    """台帳の formats からショートかを見る。

    `is_short()` は書き出したファイル名を見るので、out/ を掃除したあとは使えない。
    公開済みのものを retitle するときはこちらを使う。
    """
    return "short" in (clip.get("formats") or [])


def build_title(video_id, clip_id, body, members=()):
    """本文とメンバー名からタイトルを組み立てる。

    ショートは `metadata.short_title()` の型に通す。横型はショートの作法
    （ハッシュタグ・#shorts）を使わないので本文をそのまま使う。
    """
    _, clip = find_clip(video_id, clip_id)
    if clip_is_short(clip):
        if "#" in body:
            raise UploadBlocked(
                "ショートの --title には本文だけを渡してください。"
                "ハッシュタグは --members から組み立てます")
        return metadata.short_title(body, members)
    return metadata.validate_title(body)


def set_thumbnail(service, yt_id, video_id, clip):
    """サムネイルを設定する。失敗しても動画自体は上がっているので止めない。

    thumbnails.set は短時間に何度も呼ぶと 429 で弾かれる。クォータ超過とは
    別物で、時間を置けば通る。チャンネルの電話番号確認が未了でも 403 になる。
    """
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    from . import thumbnail as thumb_mod

    if not (config.settings().get("channel") or {}).get("custom_thumbnails"):
        # 電話番号確認が済むまで通らない。毎回50ユニット捨てて403を出すより、
        # 設定で切っておく。画像自体は作っておき、有効化したら設定できる状態にする
        try:
            thumb_mod.build_for_clip(video_id, clip)
        except Exception:                                       # noqa: BLE001
            pass
        return False

    try:
        path = thumb_mod.build_for_clip(video_id, clip)
    except Exception as e:                                      # noqa: BLE001
        print(f"! サムネイルを作れませんでした（続行）: {str(e)[:90]}")
        return False

    try:
        service.thumbnails().set(
            videoId=yt_id, media_body=MediaFileUpload(str(path))).execute()
        return True
    except HttpError as e:
        _raise_if_quota(e)
        text = str(e)
        print("! サムネイルを設定できませんでした（動画は残す）")
        if "429" in text:
            print("  差し替えの頻度制限です。時間を置いて再実行してください")
        elif "custom video thumbnails" in text or "forbidden" in text:
            # カスタムサムネイルはチャンネルの電話番号確認が前提
            print("  カスタムサムネイルにはチャンネルの確認が必要です。")
            print("  https://www.youtube.com/verify_phone_number で確認してください")
        else:
            print(f"  {text[:150]}")
        return False


def find_clip(video_id, clip_id):
    entry = ledger.load(video_id)
    if not entry:
        raise UploadBlocked(f"台帳に {video_id} がありません")
    clip = next((c for c in entry["clips"] if c["clip_id"] == clip_id), None)
    if not clip:
        raise UploadBlocked(f"{video_id} に {clip_id} がありません")
    return entry, clip


def upload_private(video_id, clip_id, title, service=None):
    """非公開でアップロードする。gate は通さない。

    非公開の動画は本人以外に見えないため、公開にはあたらない。
    BRDOCK へは「ご許諾をいただけた場合にのみ公開いたします」と伝えており、
    その約束を破らずに在庫を作れる。**public にする経路はここには無い。**
    """
    from googleapiclient.http import MediaFileUpload

    entry, clip = find_clip(video_id, clip_id)
    path = output_path(video_id, clip)

    service = service or get_service()
    ch = assert_expected_channel(service)

    body = {
        "snippet": metadata.build_body(entry, clip, title, is_short(path)),
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    request = service.videos().insert(part="snippet,status", body=body,
                                      media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  アップロード {int(status.progress() * 100)}%")

    yt_id = response["id"]
    thumb_ok = set_thumbnail(service, yt_id, video_id, clip)
    clip["upload"] = {
        "thumbnail_set": thumb_ok,
        "youtube_video_id": yt_id,
        "url": f"https://www.youtube.com/watch?v={yt_id}",
        "privacy_status": "private",
        "title": title,
        "channel_id": ch["id"],
        "channel_title": ch["title"],
    }
    ledger.put_clips(entry, [clip])
    return clip["upload"]


def delete_video(video_id, clip_id, service=None):
    """アップロード済みの動画を消す。

    YouTube は動画ファイルの差し替えができないため、作り直したものを出すには
    消して上げ直すしかない。動画IDが変わる点に注意（公開後にやると被リンクや
    再生数を失う）。非公開のうちに済ませる。
    """
    from googleapiclient.errors import HttpError

    entry, clip = find_clip(video_id, clip_id)
    up = clip.get("upload")
    if not up:
        return None

    service = service or get_service()
    try:
        service.videos().delete(id=up["youtube_video_id"]).execute()
    except HttpError as e:
        _raise_if_quota(e)
        if "404" not in str(e):
            raise
    clip["previous_upload"] = up
    clip["upload"] = None
    ledger.put_clips(entry, [clip])
    return up["youtube_video_id"]


def replace_private(video_id, clip_id, title=None, service=None):
    """作り直したものに差し替える。旧版を消してから上げ直す。"""
    entry, clip = find_clip(video_id, clip_id)
    title = title or (clip.get("upload") or {}).get("title")
    if not title:
        raise UploadBlocked(f"{clip_id} のタイトルが分かりません")

    service = service or get_service()
    old = delete_video(video_id, clip_id, service)
    info = upload_private(video_id, clip_id, title, service)
    info["replaced"] = old
    return info


def retitle(video_id, clip_id, title, service=None):
    """公開設定を触らずにタイトルだけ差し替える。

    **映像を作り直す必要が無いときは上げ直さない。** videos.update は50ユニットで
    videos.insert の1,600に対して桁が違い、動画IDも再生数も維持される。
    """
    from googleapiclient.errors import HttpError

    entry, clip = find_clip(video_id, clip_id)
    up = clip.get("upload")
    if not up:
        raise UploadBlocked(f"{clip_id} はまだアップロードされていません")
    metadata.validate_title(title, is_short=clip_is_short(clip))

    service = service or get_service()
    yt_id = up["youtube_video_id"]
    try:
        items = service.videos().list(
            part="snippet", id=yt_id).execute().get("items", [])
    except HttpError as e:
        _raise_if_quota(e)
        raise
    if not items:
        raise UploadBlocked(f"動画が見つかりません: {yt_id}")

    snippet = items[0]["snippet"]
    snippet["title"] = title[:metadata.TITLE_MAX]
    # categoryId は update に必須。読み取り専用の項目は送り返さない
    body = {"id": yt_id, "snippet": {
        k: snippet[k] for k in
        ("title", "description", "tags", "categoryId",
         "defaultLanguage", "defaultAudioLanguage") if k in snippet}}
    service.videos().update(part="snippet", body=body).execute()

    up["title"] = title
    ledger.put_clips(entry, [clip])
    return up


def publish(video_id, clip_id, service=None, segments=None):
    """非公開の動画を公開に切り替える。**gate を通ったものだけ。**

    gate が held を返す間はここで止まる。許諾の回答が来て
    permission.yaml が granted になるまで、この関数は必ず失敗する。
    """
    entry, clip = find_clip(video_id, clip_id)
    if not clip.get("upload"):
        raise UploadBlocked(f"{clip_id} はまだアップロードされていません")

    verdict = gate.evaluate(entry, clip, segments)
    if verdict["result"] != "pass":
        raise UploadBlocked(
            "ゲートを通っていないため公開しません:\n  - "
            + "\n  - ".join(verdict["reasons"]))

    service = service or get_service()
    assert_expected_channel(service)
    yt_id = clip["upload"]["youtube_video_id"]

    items = service.videos().list(part="status", id=yt_id).execute().get("items", [])
    if not items:
        raise UploadBlocked(f"動画が見つかりません: {yt_id}")
    cur = items[0]["status"]
    # update は part を丸ごと置き換える。読み取り専用の項目を送り返すとエラーになるので
    # 書き込める項目だけを拾って差し替える
    writable = ("license", "embeddable", "publicStatsViewable",
                "selfDeclaredMadeForKids")
    status = {k: cur[k] for k in writable if k in cur}
    status["privacyStatus"] = "public"
    service.videos().update(part="status",
                            body={"id": yt_id, "status": status}).execute()

    clip["upload"]["privacy_status"] = "public"
    clip["published"] = clip["upload"]["url"]
    ledger.put_clips(entry, [clip])
    gate.record_published(entry, clip)
    return clip["upload"]


def cmd_auth(args=None):
    try:
        service = get_service()
    except UploadBlocked as e:
        print(f"× {e}", file=sys.stderr)
        return 1
    ch = current_channel(service)
    if not ch:
        print("認証しましたが、チャンネルを取得できませんでした")
        return 1
    print(f"認証しました: {ch['title']}（{ch['id']}）")
    print()
    print("このチャンネルで合っていれば、config/settings.yaml に次を書いてください:")
    print("  channel:")
    print(f"    expected_channel_id: {ch['id']}")
    print()
    print(f"違っていれば {TOKEN.name} を消し、同意画面で選び直してください。")
    return 0
