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
        creds.refresh(Request())
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
    raise


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
    path = config.out_dir() / f"{video_id}_{clip_id}_short.mp4"
    if not path.exists():
        raise UploadBlocked(f"{path} がありません。先に書き出してください")

    service = service or get_service()
    ch = assert_expected_channel(service)

    body = {
        "snippet": metadata.build_body(entry, clip, title),
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
    clip["upload"] = {
        "youtube_video_id": yt_id,
        "url": f"https://www.youtube.com/watch?v={yt_id}",
        "privacy_status": "private",
        "title": title,
        "channel_id": ch["id"],
        "channel_title": ch["title"],
    }
    ledger.put_clips(entry, [clip])
    return clip["upload"]


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
