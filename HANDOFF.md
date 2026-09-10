# HANDOFF

最終更新: 2026-09-10（同日2回目。分析のあと、意見を実装した）

## いま何をしているのか

コムドット切り抜きの制作と投稿。**在庫18本の予約を入れ、判定日を決めた。ここからは待って測る。**

いま立っている場所:

- **2026-09-11 07:00 〜 09-19 18:00 の18枠を `--arm` 済み**（下の 3）。
  YouTube 側に `publishAt` が入っていることを API で確認した
- **判定日は 2026-09-29。** 合格線は `config/settings.yaml` の `distribution_target` に
  **結果を見る前に**書いてある（下の 4）。**あとから下げないこと**
- **除外2本を削除した**（下の 2）。09-02 から3回持ち越していた案件が片づいた
- **残作業が1つ。** Google Cloud で **YouTube Analytics API が未有効**なので
  `distribution_check.py` の API 取得部分がまだ動かない（下の「次にやること 1」）
- 許諾は運営者の再確認で `granted` を維持。**根拠はいまも申告だけ**（下の 5）

## 今回やったこと（2026-09-10・2回目）

1. Studio と API でアナリティクスを実測した → [`docs/analytics-2026-09-10.md`](docs/analytics-2026-09-10.md)
2. **除外2本を API で削除し、台帳に記録した**（下の 2）
3. **空振りした15枠を組み直し、18枠を `--arm` した**（下の 3）
4. **配信の判定基準を `settings.yaml` に固定し、判定器を作った**（下の 4）
5. **アナリティクス用の別トークンを足した**（下の 6）
6. 切り抜きの型と「時間を使わないもの」を [`docs/clip-policy.md`](docs/clip-policy.md) に書いた

変更したファイル:
`clipper/distribution.py`・`scripts/distribution_check.py`・`tests/test_distribution.py`・
`docs/clip-policy.md`（すべて新規）/ `clipper/upload.py` / `clipper/cli.py` /
`config/settings.yaml` / `config/permission.yaml` / `config/schedule.yaml` /
`scripts/build_schedule.py` / `.gitignore` / `data/videos/*.json` / `HANDOFF.md`

## 検証済みの事実（実際に画面に出た出力だけ）

### 1. アナリティクスの実測

期間 2026/08/12〜09/08 の28日。**インプレッション467回（1本あたり29回）、
ショートフィード経由 4.7%（≒3回）、登録者0。** 09-02 の測定から**桁が動いていない**。

**09-02 に公開した2本は、09-04 から09-10 の6日間で増分0だった**（8→8、7→7）。
「再開後17倍」は front-load を見ていただけ。全部 [`docs/analytics-2026-09-10.md`](docs/analytics-2026-09-10.md)。

トークンの7日失効は起きなかった（09-03 発行のトークンが今日通った）。**この論点は閉じた。**

### 2. 除外2本を削除した（**取り消せない。実行済み**）

```
削除しました: cTzbNUFi9Iw
削除しました: hbRhnrvPk-k
台帳を更新: 2件
確認: videos.list が返した件数 = 0（0なら削除済み）
```

`RGm5F2m12as` 由来（外部の催眠術師が主役）。台帳の該当クリップに
`privacy_status: deleted` / `deleted_at` / `deleted_reason` を書いた。

**この2本はインプレッション63回・72回で全体の29%を占めていた。**
次の測定で数字が下がるが、**それは悪化ではない。**

### 3. 18枠を予約した（`clipper schedule --arm`）

`python scripts/build_schedule.py 2026-09-11 2` で組み直してから arm。

```
予約した: 18件
publishAt が入っている: 18/18
```

2026-09-11 07:00 〜 2026-09-19 18:00、1日2本。JST 07:00 が UTC 前日22:00 になっているのも確認済み。

`build_schedule.py` を1つ直した。**未アップロード（`youtube_video_id` が無い）ものを
枠に入れないようにした。** `M7ZxIL_b39E` の8本は書き出し済みだが未アップロードなので、
在庫26本のうち**18本だけが枠に入る**。

### 4. 配信の判定基準を固定し、判定器を作った

`config/settings.yaml` の `distribution_target`:

| 項目 | 値 |
|---|---:|
| 基準（2026-09-10 実測） | 1本あたり29回/28日・フィード4.7% |
| 合格線 | 1本あたり**100回**・フィード**20%** |
| 判定日 | **2026-09-29** |
| unclear の閾値 | 基準の1.5倍 |

判定は `clipper/distribution.py` の `evaluate()`。verdict は
`early` / `insufficient` / `pass` / `unclear` / `fail` の5つ。
**`fail` は「投稿頻度が原因という仮説（H1）の否定」を意味する。**

```
$ python -m pytest tests/ -q
169 passed, 4 warnings in 1.18s
```

`tests/test_distribution.py` に21件。**設定ファイルの現在値ではなくロジックを固定している**
（gate のテストと同じ方針）。「どちらか一方の指標だけでも判定できる」ことも含む。

### 5. 許諾は `granted` のまま。根拠は運営者の申告だけ

2026-09-10 に運営者が「確認できた」と回答したので `status: granted` を維持し、投稿を再開した。
**回答文はいまもリポジトリに無く、出どころ（メール／電話／フォーム／SNS）も記録できていない。**
`conditions` は全部 `unknown` のまま。**推測で埋めていない。**
経緯は `config/permission.yaml` の冒頭コメント。

### 6. アナリティクス用の別トークンを足した

**投稿に使っている `token.json` には触っていない。** リファクタ後に `clipper auth` を
実行して従来どおり通ることを確認済み:

```
認証しました: コムドット名場面ch【切り抜き】（UCoT2TYsxzH4t42C2oF-KrAw）
```

`python -m clipper auth --analytics` で `token.json.analytics`（`yt-analytics.readonly` のみ）を
別に作る。**同意は通り、トークンは保存された。** `.gitignore` に明示行も足した。

## 未検証のもの

- **`scripts/distribution_check.py` の API 取得部分は一度も通っていない。**
  Google Cloud プロジェクト `120171737302` で **YouTube Analytics API が未有効**のため
  403（`accessNotConfigured`）。判定ロジックは単体テスト済みだが、
  **実データで動いたところは見ていない**（下の「次にやること 1」）
- **サムネイルのインプレッションが Analytics API で取れるかは未確認。**
  取れなければ Studio から `--impressions` で手渡しする作りにしてある
- **予約が実際に発火して公開されるかは 2026-09-11 07:00 まで分からない**
- **許諾の回答文を見ていない**（上の 5）
- **尺の実験はまだ一度もしていない。** `short_experiment` は枠だけ
- **切り抜きの型（1人の一言）はまだコードに反映していない。** `docs/clip-policy.md` に方針のみ
- **`M7ZxIL_b39E` の8本は未アップロード。** 各6コマしか見ていない（第三者は48コマで0人）
- **アップロード済み6本のタイトルは旧型式**（メンバー名・`#shorts` なし）
- `fDiW0YbLd-Q` の飲酒が年齢制限を受けるかは未確認
- **`G2gXaVSnOQY`（北海道前編）は未着手。** すすきの回なので第三者リスクが高い

## 次にやること

**すべて `Set-Location` と環境変数を先に打つこと**（PowerShell 5.1。`&&` は使えない）:

```powershell
Set-Location C:/Users/oshim/Documents/projects/com.-youtube
$env:CLIPPER_CREDENTIALS_DIR = "C:/Users/oshim/Documents/projects/com.-youtube"
```

### 1. YouTube Analytics API を有効化する（**運営者。1クリック**）

```
https://console.developers.google.com/apis/api/youtubeanalytics.googleapis.com/overview?project=120171737302
```

有効化したら数分待って:

```powershell
python scripts/distribution_check.py
```

流入経路の内訳と判定（いまは `early`）が出れば通っている。
**インプレッションの行が「取れなかった」と出たら**、Studio の詳細モードで読んで:

```powershell
python scripts/distribution_check.py --impressions <Studio の値>
```

### 2. 予約が発火したか見る（2026-09-11 の朝）

```powershell
python scripts/account_audit.py
```

`NoXz0Oa9fpI` が public になっていれば発火している。
**1本目が出なかったら予約の仕組みが壊れているということ**なので、そこで止めて調べる。

### 3. 2026-09-29 に判定する（**この日まで作り方を変えない**）

```powershell
python scripts/distribution_check.py
```

- `pass` → 配信は動いた。**そこで初めて中身の優劣を比べる母数になる**
- `unclear` → 観測を延ばす。**合格線は下げない**
- `fail` → 投稿頻度が原因という仮説は否定。次は H2（チャンネル自体の信頼度）を測る

理由は [`docs/clip-policy.md`](docs/clip-policy.md)。**判定日より前に作り方をいじると、
何が効いたのか分からなくなる。**

### 4. 旧型式のタイトル6本を直す（判定日より前でよい。露出に影響しない）

```powershell
python -m clipper retitle <video_id> <clip_id> --title "<本文>" --members <確認した名前>
```

50ユニット／本。動画IDも再生数も維持される。

### 5. 在庫が切れる 2026-09-20 以降の補充（**判定を待ってからでよい**）

`M7ZxIL_b39E` の8本が `out/` にある。上げるなら1本ずつ、`--members` は
映像で確認できた名前だけ（`docs/third-party-audit-2026-09-04.md`）:

```powershell
python -m clipper upload M7ZxIL_b39E auto04 --title "<本文>" --members やまと,ゆうた,ひゅうが,ゆうま,あむぎり
```

**尺の実験をするならここが最初の機会。** `settings.yaml` の
`formats.short_experiment.max_seconds: 35` で切り直し、55〜68秒のものと交互に出す。

## 触ってはいけないところ

### 権利

- **コラボ回・ファン参加回・イベント回は第三者の肖像の問題で使えない。**
  許諾を依頼したのは BRDOCK だけで、第三者はその射程外
- **`--members` に推測を渡さない。** 映像で確認したものだけ。名簿外は弾かれるが、
  **名簿内の別人の名前は弾けない**
- **自動判定を通っても使えるとは限らない。実測で4回外している**
  （`fbKne9hTmgA` 体育館の一般の方 / `MgO0lCUtlx4 auto01` 高校対中学の試合 /
  `RGm5F2m12as` 外部の催眠術師 / `zvM7bkbavDQ` ファン参加）。
  **書き出したら必ず `audit_third_parties.py` でコマを見る**
- 動画ごと除外: `RGm5F2m12as` / `fbKne9hTmgA` / `ARuwTdvqJJA` / `lCKD3eRA6nE`
- `Fb9bO8V9oNA`（目隠しかくれんぼ）は CDF シャッフルコラボ回。素材にしない
- `abW8zkEwEW4/auto03` は下ネタのため素材にしない

### 運用

- **`clipper schedule --rebuild` を打たない**（上の「次にやること 3」）
- **1日の公開は2本まで**（`settings.yaml` の `max_publish_per_day`）。gate が数えている。
  gate の当日上限は**スロットの日付ではなく「今日」の公開本数**を見るので、
  今日2本出したあとは未来日付のスロットまで巻き添えで止まる。
  **公開を増やすために安全弁を緩める変更は勝手に入れない**
- **収益化を ON にすると gate が全部止まる**（`conditions.monetization` が `allowed` 以外のため）。
  `channel.monetization_enabled` は API では取れないので Studio を見て手で書く欄
- カスタムサムネイル不可・15分超不可（電話番号確認ができないため）。**再依頼しない**
- **`config/settings.yaml` の `distribution_target` の合格線を下げない。**
  結果を見る前に決めた数字で、下げれば必ず「達成」できてしまう。
  動かすときは理由をコミットメッセージに残すこと
- **2026-09-29 の判定日より前に切り抜きの作り方を変えない。**
  変えると何が効いたのか分からなくなる（[`docs/clip-policy.md`](docs/clip-policy.md)）

### 認証とリポジトリ

- **アナリティクス用は `token.json.analytics` という別トークン。**
  `token.json`（投稿用）とは独立していて、片方の取り直しが他方を壊さない。
  スコープは `yt-analytics.readonly` だけ。**投稿用のトークンを analytics 用に流用しない**
- **`token.json` / `client_secret.json` を退避するとき、リポジトリ内に置かない。**
  `.gitignore` は `token.json*` などに広げたが、**別名（例: `auth_backup.json`）にすれば
  素通りする**。退避先はリポジトリの外にすること
- **このリポジトリは PUBLIC。** `git add -A` の前に `git status --short` で中身を見る
- 端末は **Windows PowerShell 5.1**。`VAR=値 コマンド` と `&&` はどちらも使えない
  （`&&` はパースエラーで**行ごと何も実行されない**）。環境変数は `$env:NAME = "値"` を
  別行で、逐次実行は `;` でつなぐ。**Claude 側の Bash ツールは Git Bash なので書き分けること**
