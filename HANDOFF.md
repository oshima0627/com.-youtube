# HANDOFF

最終更新: 2026-09-02

## いま何をしているのか

コムドット切り抜きの制作と投稿。**投稿を再開し、在庫を9日分にした。**

- 認証を復旧（下の C）／トークンの7日失効は当てはまらないと確認（下の I）
- 許諾を `granted` にした（下の D。**根拠は運営者の申告のみ**）
- **2026-09-02 に2本を公開**（下の F）。**本日の上限2本に到達済み**
- 新素材 `Gsd-7b4Kdx8` から**6本を追加で書き出し・アップロード**（下の J）
- **在庫18本 ＝ 9日分**が非公開。順番は [`docs/post-plan.md`](docs/post-plan.md)
- `config/schedule.yaml` に**18枠の計画を書いた。予約はまだ入れていない**（下の K）
- **git 履歴に混入していた OAuth 認証情報を除去し、push を復旧した**（下の M）。
  **漏れた refresh_token の失効はまだ済んでいない**（下の「次にやること 0」）

## 今回やったこと（2026-09-02）

1. 公開済み14本の実績を実測し、競合ショートと突き合わせた → `docs/analytics-2026-09-02.md`
2. Studio をブラウザで開いてインプレッション数を読んだ（下の H）
3. ショートのタイトルにメンバー名と `#shorts` を必須にした（下の B）
4. `ARuwTdvqJJA`（40組コラボ）を除外に追加
5. 新しいショートを7本書き出した（下の A）
6. 台帳の `privacy_status` を実測に合わせた
7. 認証復旧・許諾更新・14本アップロード・2本公開（下の C〜F）
8. **トークンの7日失効を調べ直した。条件に当てはまっていなかった**（下の I）
9. **`token.json.expired-20260814` を git 履歴から除去し、`.gitignore` を広げた**（下の M）

変更したファイル:
`clipper/metadata.py` / `clipper/upload.py` / `clipper/cli.py` /
`config/exclusions.yaml` / `config/permission.yaml` / `data/videos/*.json` /
`docs/analytics-2026-09-02.md`・`docs/post-plan.md`（新規）/
`scripts/week_plan.py`・`sync_privacy.py`・`sheet_at.py`（新規）/
`tests/test_metadata.py`（新規）/ `tests/test_gate.py` / `tests/test_upload.py` /
`README.md` / `HANDOFF.md`

## 検証済みの事実（実際に画面に出た出力のみ）

### A. 新しく書き出した7本は全部、第三者点検を通してある

| クリップ | 区間 | 場所と人 |
|---|---|---|
| `xBpumDn8QYE/man02` | 1:32:20-1:33:22 | 座敷。**メンバー2人だけ**（8コマ目視） |
| `8DDHTuwdbyQ/auto03` | 57:44-58:51 | 座敷。**4人だけ**（6コマ目視） |
| `8DDHTuwdbyQ/auto05` | 1:02:45-1:03:46 | 同上（6コマ目視） |
| `8DDHTuwdbyQ/man01` | 1:06:11-1:07:19 | 同上（6コマ目視） |
| `abW8zkEwEW4/auto06` | 1:15-2:22 | ソファ。**5人だけ**（9コマ目視） |
| `abW8zkEwEW4/auto04` | 37:33-38:40 | 車内。**2人だけ**（6コマ目視） |
| `abW8zkEwEW4/auto05` | 1:20:27-1:21:30 | 室内。**5人だけ**（6コマ目視） |

- `8DDHTuwdbyQ` は「やまとの誕生日をやまと抜きで」の回。
  **画面に4人しかいない＝やまと以外の4人**がメンバー特定の根拠
- `abW8zkEwEW4/auto06` の LINE オーバーレイは拡大して確認。**メンバー本人の写真とアイコン**
- 点検シートは `work/<video_id>/<clip_id>_audit.png`（git 追跡外）
- **`8DDHTuwdbyQ/auto04` は捨てた。** 冒頭テロップが「知ってるよね？雷獣チャンネル」で
  見出しと合わず、`man01` に切り直した。台帳に理由を書いて `excluded` にしてある
- **`abW8zkEwEW4/auto03` は採らない。** 下ネタが続く区間

### B. ショートのタイトルの型を機械の検査にした

型は docs にあったが `short_title()` がどこからも呼ばれておらず、素通しだった。

- `SHORT_TAGS` = `#コムドット #コムドット切り抜き #shorts`
- `short_title(body, members)` が名簿 `metadata.MEMBERS` 外の名前を弾く
- 100文字超は**末尾のタグを丸ごと落とす**（途中で切らない）
- `validate_title(title, is_short=True)` が `#shorts` とメンバー名を必須にする
- CLI に `--members` と `retitle` サブコマンドを追加

```
$ python -m pytest -q
141 passed, 4 warnings in 1.01s
```

**`--members` は映像で確認できたメンバーだけ。** 字幕からは決められない
（公開済みショート19本中16本は区間内の字幕に名前が出ない）。

### C. 認証を復旧した（worktree から使えるようにした）

`client_secret.json` / `token.json` は本体側にしかなく、**worktree への複製は
環境側でブロックされた。** 環境変数で本体を指せるようにしてある。

```powershell
$env:CLIPPER_CREDENTIALS_DIR = "C:/Users/oshim/Documents/projects/com.-youtube"
python -m clipper ...
```

**この機械の端末は Windows PowerShell 5.1。** `VAR=値 コマンド`（環境変数の前置き）と
`&&` はどちらも使えない。`&&` はパースエラーになり、**行ごと何も実行されない**。
環境変数は `$env:NAME = "値"` を別行で、逐次実行は `;` でつなぐ。
（Claude 側の Bash ツールは Git Bash なので bash 記法が通る。**貼り付ける先で書き分けること。**）

古いトークンは `invalid_grant` だったので退避して `clipper auth` をやり直した
（同意画面はブラウザで通した）。結果:

```
channel: {'id': 'UCoT2TYsxzH4t42C2oF-KrAw', 'title': 'コムドット名場面ch【切り抜き】'}
```

**同意画面のブランドアカウント名は「コムドットのおもしろ切り抜きチャンネル」で、
チャンネル名と違う。** 名前で探すと迷う。選んだあと `UCoT2TYsxzH4t42C2oF-KrAw`
が出れば正しい。退避した古いトークンは削除済み。

**このトークンが7日で失効するという前提は誤りだった。** 下の I。

### D. 許諾を granted にした（根拠は運営者の申告のみ）

**2026-09-02、運営者から「BRDOCK の許諾の回答が来た」との申告を受けて
`config/permission.yaml` を `granted` にした。**

- `responded_at: 2026-09-02`
- **回答文そのものはリポジトリに保存されていない**
- `conditions`（収益化可否・クレジット要否・本人画像の可否）は **unknown のまま**

この変更で `tests/test_gate.py` の2件が落ちた（実物の permission.yaml を読んで
pending 前提で書いてあった）。**設定の現在値ではなくゲートの挙動を固定するよう、
monkeypatch で pending / denied / granted を作って書き直した。**

### E. 14本すべてアップロード済み（新しい8本は今回）

| クリップ | YouTube ID |
|---|---|
| `8DDHTuwdbyQ/auto03` | `H5v_FFA73So` ← **公開済** |
| `abW8zkEwEW4/auto06` | `sR58Xt36Xco` ← **公開済** |
| `8DDHTuwdbyQ/auto05` | `bjPdC-HDT4E` |
| `abW8zkEwEW4/auto04` | `tUuz9i0ZfMc` |
| `xBpumDn8QYE/man01` | `V6BPliNEgUk` |
| `8DDHTuwdbyQ/man01` | `mrr0vlt-FVQ` |
| `abW8zkEwEW4/auto05` | `WkzU8t6h1sQ` |
| `xBpumDn8QYE/man02` | `gvQBGy1kFp4` |

8本 × 1,600ユニット = 12,800。**既定クォータ10,000を超えるはずだが通った。**
クォータが引き上げられている可能性がある（未確認）。

### F. 本日2本を公開した（2026-09-02）

```
✓ 公開しました: https://www.youtube.com/watch?v=H5v_FFA73So
✓ 公開しました: https://www.youtube.com/watch?v=sR58Xt36Xco
```

yt-dlp で両方 `public` を確認。3本目は gate が止める:

```
3本目の gate: held ['本日の投稿上限 2 本に達している']
```

### G. 露出がほぼ出ていない（作る前の問題）

再開前の公開14本は**合計再生45回**、ショート中央値3回。競合の中央値は
29,500〜159,000で、一番伸びなかった1本でも2,900回。

### H. 止まっているのは配信側（Studio の画面で確認）

期間 2026/08/04〜08/31。

| 指標 | 値 |
|---|---:|
| **サムネイルのインプレッション数** | **355**（14本・28日。1本あたり25回） |
| サムネイルのクリック率 | 1.4% |
| チャンネル登録者 | 0 |

```
YouTube 検索        86.4%
直接入力または不明   6.8%
ショート フィード    4.6%   ← 45回の4.6% ＝ およそ2回
ブラウジング機能     2.3%

視聴を継続 60.0%  /  スワイプして消去 40.0%
```

制限も著作権の申し立ても無し（通知列は全13本が「–」）。

**中身でも設定でもなく、配信が出ていない。** 出た分の6割は見られている。
**尺・タイトル・切り抜き地点をいじってもこの数字は動かない。**
今回の再開（11日ぶりの投稿・毎日2本）が効くかは、これから測る。

### I. トークンの7日失効は、この設定には当てはまらない（コンソールで確認）

2026-09-02 に Google Cloud コンソールを実際に見た。

```
Google Auth Platform → 対象
  公開ステータス : 本番環境        ← 「テスト中」ではない
  ユーザーの種類 : 外部
  OAuth ユーザー数の上限 : 2人 / 100

Google Auth Platform → 検証センター
  「アプリは機密性の高いスコープや制限付きスコープをリクエストしていないため、
    検証は必要ありません」
```

**7日で失効するのは「テスト中」のときだけ。** このプロジェクトは本番環境なので
条件に当てはまらない。`docs/youtube-api-setup.md` に「恒久的に直すには Google の
審査が要る」と書いてあったが**誤りだったので書き直した。**

同意画面の「データアクセス」にスコープが1つも登録されていないため、Google からは
機微スコープを要求しないアプリに見えている。実行時には3つのスコープを要求するので
**同意時に「Google で確認されていません」の警告が出る。想定どおり。**

トークンの中身（`token.json`）:

```
refresh_token あり: True
expiry: 2026-09-02T08:42:44Z   ← アクセストークンの期限。リフレッシュとは別物
scopes: youtube.upload / youtube.readonly / youtube.force-ssl
生存確認: {'id': 'UCoT2TYsxzH4t42C2oF-KrAw', 'title': 'コムドット名場面ch【切り抜き】'}
```

**Google Cloud の設定は何も変更していない。** すでに望みの状態だった。

### J. 新素材 Gsd-7b4Kdx8 から6本（第三者点検済み・アップロード済み）

`@comdot` の直近10本を screen した結果、**未採掘で使えるのは
`Gsd-7b4Kdx8`（第4回ペア人気投票、08-21、78分）だけ**だった。

| 除外された動画 | 理由 |
|---|---|
| `ARuwTdvqJJA` | 40組コラボ（既に exclusions） |
| `vIhcQ9IVUuQ` | 概要欄に「シャッフルコラボ」 |
| `tvpzuKIW71o` / `2Ip54dw8F_M` / `HNAKXt0d31w` | メンバーシップ限定 |
| `G2gXaVSnOQY`（北海道前編） | screen は通るが未着手。すすきの回なので第三者リスク高 |

書き出した6本。**全部6コマを目視し、白壁の部屋にメンバー5人だけ**を確認した。

| クリップ | 区間 | YouTube ID | 焼き込みテロップで確認した文言 |
|---|---|---|---|
| `auto01` | 28:10-29:14 | `9wYgoaYymB8` | 「第1位」「32,961票」「遂に初期メン王朝が幕を下ろす」 |
| `auto02` | 45:39-46:46 | `Yxu5FfDaQ0c` | 「4位まで終了し未だに点呼されないぎり君」 |
| `auto03` | 1:01:26-1:02:33 | `RuSV7tWQlp0` | 「下剋上コンビ1万票おめでとう!!」「よく続けてきた」 |
| `auto04` | 34:39-35:47 | `XJBJenehfrw` | 「ゆうたが1位じゃなくなったぐらいのインパクトだよね」 |
| `auto05` | 18:15-19:22 | `NoXz0Oa9fpI` | 「ひゅうがのビリ予想」「おじさんの家だろ」 |
| `auto06` | 49:45-50:53 | `owY3Or_qcJI` | 「第5位」「17,258票」「心の余裕が違いすぎるだろ」 |

**ASR は当てにならないことがまた出た。** auto06 の字幕は「ヤニヤニ」と読めたが、
画面のテロップは「師弟」で第5位。**見出しはテロップを見てから書いた。**

### K. 予約計画は書いたが、予約は入れていない

`scripts/build_schedule.py` を追加し、`config/schedule.yaml` に18枠
（2026-09-03〜09-11、07:00 と 18:00）を書いた。
**`clipper schedule --rebuild` を使っていない。** 理由は2つ:

1. `build_plan()` はショート**1本/日**しか置かない。運用は2本/日
2. 既存の `slots` は「2026-08-18 に Studio で実際に入っていた予約の写し」という
   記録なので、`archive` キーへ退避してから新しい `slots` を書いた（10件を保持）

**今日は arm できない。** gate が全スロットを止める:

```
先頭スロット Gsd-7b4Kdx8/auto05 -> held ['本日の投稿上限 2 本に達している']
```

`gate.evaluate` の当日上限は**スロットの日付ではなく「今日」の公開本数**を見ている。
今日すでに2本公開したので、未来日付のスロットまで巻き添えで止まる。
**設計としては直す価値があるが、公開を増やすために安全弁を緩める変更なので
勝手に入れていない。** 明日以降に arm すれば通る。

### L. 台帳の同時書き込みで lost update が起きた（対処済み）

レンダリングを2プロセス同時に走らせたところ、後から `ledger.put_clips` した側が
先の書き込みを上書きし、**auto05 / auto06 の `formats` `hook` `footer`
`planned_title` が消えた。** アップロード時に `KeyError: 'planned_title'` で停止。

書き出した mp4 は `out/` に残っていたので、台帳だけ復元してアップロードし直した。
現在は6本とも `formats: ['short']` と `upload.youtube_video_id` が入っている。

**`ledger.put_clips` は読み込み→全体書き戻しなので、同じ動画の台帳を
複数プロセスから同時に触らないこと。**

### M. git 履歴に混入していた OAuth 認証情報を除去した（2026-09-02）

GitHub の Push Protection が push を拒否していた。原因は自動コミット2件。

```
45bc225 chore: 作業終了時の自動コミット（2026-09-02 16:45）  → token.json.expired-20260814 を追加
fd65f6d chore: 作業終了時の自動コミット（2026-09-02 17:01）  → 同ファイルを削除
```

**そのファイルに入っていたキー**（値は出力していない）:

```
token / refresh_token / client_id / client_secret / scopes / expiry / token_uri / account
```

sha256 で突き合わせた結果:

| 対象 | 判定 |
|---|---|
| 漏れた `refresh_token` vs 現行 `token.json` の `refresh_token` | **不一致**（別の grant） |
| 漏れた `client_secret` vs 現行 `client_secret.json` | **完全一致** |

**GitHub には一度も到達していない。** 全参照（`refs/remotes` を含む）を走査して、
該当パスがリモート側の履歴に存在しないことを確認した。露出はローカルのみ。
なお `client_secret.json` の種別は `installed`（デスクトップアプリ）。

やったこと:

- `45bc225` は当該ファイルの**追加のみ**、`fd65f6d` は**削除のみ**で差し引きゼロだったため、
  この2コミットを落として `809b655` だけを `origin/main` の上に載せ直した（`git filter-repo` は不要だった）
- 書き換え後の木が元の `c5f8ed5` と一致することを確認（`git diff --stat` が空）
- `.gitignore` を `token.json` → `token.json*` / `client_secret.json*` / `*.token.json` /
  `*credentials*.json` に広げた
- バックアップタグを削除し、`git reflog expire --expire=now --all` ＋ `git gc --prune=now` を実行。
  **blob `7379f9d` はローカルからも消えた**（`git cat-file -e` が失敗する）

検証の出力:

```
$ git diff --stat backup/pre-secret-rewrite-20260902 HEAD
（空）

$ git check-ignore -v token.json.expired-20260814
.gitignore:14:token.json*	token.json.expired-20260814

$ python -m pytest -q
143 passed, 4 warnings in 1.37s

$ git push origin HEAD:main
   25b3f03..c6ed1d2  HEAD -> main
```

ローカルの `main` も `origin/main` に合わせ直した（旧 `main` はシークレット入りの
`c5f8ed5` を指していた）。**該当コミットを含むローカル参照はもう無い。**

## 未検証のもの

- **書き出した14本のどれも通しで再生していない。** 見たのは各1〜3コマと、元素材の6〜9コマ
- **許諾の回答文を見ていない。** granted の根拠は運営者の申告だけ
- **アップロード済み6本のタイトルは旧型式**（メンバー名・`#shorts` なし）。
  直すには誰が映っているかの確認が要る
- **投稿再開でインプレッションが増えるかは未検証。** これが今回いちばん測りたいこと
- **`Gsd-7b4Kdx8` の6本は書き出し直後の1コマしか見ていない。** 通しでは未確認
- **`G2gXaVSnOQY`（北海道前編）は未着手。** screen は通るが、すすきの回なので
  第三者の映り込みを実際に見るまで使えるか分からない
- **クォータの実際の上限を確認していない。** 12,800ユニット分が通った理由は不明
- **今日のトークンが7日後も生きているかは未検証。** 「テスト中ではない」ことは
  確認したが、実際に9日後まで持つかは**2026-09-09 以降に確かめるまで分からない**
- 失効しうる他の条件（6ヶ月未使用・パスワード変更・アクセス取り消し）は
  Google の一般的な仕様であって、こちらで実測したものではない
- `xBpumDn8QYE` の飲酒描写が年齢制限を受けるかは未確認
- `wKuTNfA6Xhg/auto03`（冒頭 10-78秒）は未点検・未書き出し。予備
- **漏れた refresh_token を失効させていない。** このセッションからは
  シークレットを読んで外部APIへ送る操作がブロックされたため実行できなかった。
  **生きているかどうかも未確認**（`invalid_grant` だったという記録はあるが今回は叩いていない）
- **`client_secret` をローテーションしていない。** 現行のものと同一の値が
  ローカル履歴に載っていた。GitHub には出ていないが、入れ替えは済んでいない

## 次にやること

### 0. 【最優先】漏れた OAuth 認証情報を失効・再発行する（要ブラウザ操作）

**Claude 側では実行できない**（シークレットを外部へ送る操作がブロックされる）。手で行う。

1. **アプリのアクセスを取り消す** — https://myaccount.google.com/permissions
   該当アプリを選んで「アクセス権を削除」。これで**この client に紐づく
   refresh_token が全部無効になる**（漏れたものも、現行のものも）
2. **クライアントシークレットを入れ替える** — Google Cloud Console →
   「API とサービス」→「認証情報」→ 該当の OAuth 2.0 クライアント ID →
   シークレットを追加して、**古い方を削除**
3. 新しい `client_secret.json` をダウンロードして
   `C:/Users/oshim/Documents/projects/com.-youtube/client_secret.json` を置き換える
4. `token.json` を削除して認証をやり直す:

```powershell
Set-Location C:/Users/oshim/Documents/projects/com.-youtube
Remove-Item token.json
$env:CLIPPER_CREDENTIALS_DIR = "C:/Users/oshim/Documents/projects/com.-youtube"
python -m clipper auth
```

同意画面のブランドアカウントは「コムドットのおもしろ切り抜きチャンネル」。
選んだあと `UCoT2TYsxzH4t42C2oF-KrAw` が出れば正しい（上の C）。

**1 をやると現行トークンも死ぬので、その日の公開を済ませてから行うと手戻りが少ない。**

### 1. 明日（2026-09-03）以降に投稿を続ける。在庫18本 ＝ 9日分

**計画は `config/schedule.yaml` に書いてある。** 先頭は
`Gsd-7b4Kdx8/auto05` と `Gsd-7b4Kdx8/auto01`。

自動化する（推奨。1回で18枠ぶん仕掛かる）:

```powershell
Set-Location C:/Users/oshim/Documents/projects/com.-youtube/.claude/worktrees/video-creation-scheduling-2370b5
$env:CLIPPER_CREDENTIALS_DIR = "C:/Users/oshim/Documents/projects/com.-youtube"
python -m clipper schedule            # 計画を見るだけ
python -m clipper schedule --arm      # 実際に予約を入れる（明日以降でないと通らない）
```

手で出す:

```powershell
python -m clipper publish Gsd-7b4Kdx8 auto05
python -m clipper publish Gsd-7b4Kdx8 auto01
```

計画を組み直すときは `python scripts/build_schedule.py [開始日] [1日の本数]`。
**`clipper schedule --rebuild` は使わない**（記録を消し、1本/日になる）。

### 2. 1週間後にインプレッションを測り直す（2026-09-09 ごろ）

Studio → アナリティクス → 右上「詳細モード」。**355回から動いたかを見る。**
動かなければ、投稿頻度は原因ではなかったということ。

### 3. トークンが生きているかを時々見る（1ユニット）

```powershell
Set-Location C:/Users/oshim/Documents/projects/com.-youtube/.claude/worktrees/video-creation-scheduling-2370b5
$env:CLIPPER_CREDENTIALS_DIR = "C:/Users/oshim/Documents/projects/com.-youtube"
python -m clipper auth
```

チャンネル名と `UCoT2TYsxzH4t42C2oF-KrAw` が出れば生きている。
**7日で切れる設定ではない**（上の I）が、切れたら `token.json` を消して同じコマンド。
**2026-09-09 を過ぎても生きていれば、7日失効が無いことの実証になる。**

### 4. 除外2本を削除する（Studio で手動）

`cTzbNUFi9Iw` と `hbRhnrvPk-k`。素材 `RGm5F2m12as` 由来で外部の催眠術師が映る。
**現在も公開されている。**

### 5. 許諾の回答文を記録に残す

回答文を `docs/permission-request.md` に貼り、条件（収益化・クレジット・
本人画像）を `permission.yaml` の `conditions` へ書き写す。
**いまの記録は申告だけが根拠。**

### 6. 旧型式のタイトル6本を直す

```bash
python -m clipper retitle <video_id> <clip_id> --title "<本文>" --members <確認した名前>
```

50ユニット／本。**動画IDも再生数も維持される。**
`cTzbNUFi9Iw` / `hbRhnrvPk-k` は削除予定なので直さない。

### 7. 素材を足す

使える新着が `xBpumDn8QYE`（08-26）しかない。在庫は6日で尽きる。

## 触ってはいけないところ

- **`token.json` / `client_secret.json` を退避するとき、リポジトリ内に置かない。**
  `.gitignore` は `token.json*` などに広げたが、自動コミットは追跡外のファイルを拾わないだけで、
  **別名（例: `auth_backup.json`）にすれば素通りする**。退避先はリポジトリの外にする
- **このリポジトリは PUBLIC**（`gh repo view --json visibility` で確認）。
  CLAUDE.md にあった「private」という記述は誤りだったので 2026-09-02 に修正済み

- **`clipper schedule --rebuild` を打たない。** `config/schedule.yaml` の `slots` は
  「2026-08-18 に Studio で実際に入っていた予約の写し」という記録で、上書きすると消える。
  投稿順は `scripts/week_plan.py`（`docs/post-plan.md`）で出す
- **`--members` に推測を渡さない。** 映像で確認したものだけ。名簿外は弾かれるが、
  **名簿内の別人の名前は弾けない**
- **1日の公開は2本まで**（`settings.yaml` の `max_publish_per_day`）。gate が数えている
- `RGm5F2m12as` / `fbKne9hTmgA` / `ARuwTdvqJJA` は動画ごと除外
- `Fb9bO8V9oNA`（目隠しかくれんぼ）は CDF シャッフルコラボ回。素材にしない
- `abW8zkEwEW4/auto03` は下ネタのため素材にしない
- カスタムサムネイル不可・15分超不可（電話番号確認ができないため）。再依頼しない
- **コラボ回・ファン参加回は第三者の肖像の問題で使えない。**
  `xBpumDn8QYE` の自動候補の上位はファン・通行人とのやり取り。そのまま書き出さない
