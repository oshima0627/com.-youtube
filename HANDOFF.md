# HANDOFF

最終更新: 2026-09-04

## いま何をしているのか

コムドット切り抜きの制作と投稿。**在庫は18本＝9日分あり、詰まっているのは制作ではなく配信。**

いま立っている場所:

- **配信が出ていない**のが最大の問題。インプレッション355回（28日・14本）。
  投稿を再開した2本だけ数字が違う（下の 2）。**09-09 ごろに測り直すのが次の山**
- 認証は新プロジェクト `comdot-meibamen` で稼働中。2026-09-04 に `clipper auth` 成功を確認
- **許諾の回答文はどこにも無い**（下の 1）。`permission.yaml` は `granted` のままだが、
  裏づけが取れていない。**ここが未解決の最大の risk**
- **`M7ZxIL_b39E`（マクドナルド過注文人狼）の書き出しが途中**（下の「次にやること 0」）

## 今回やったこと（2026-09-04）

1. **収益化の許諾条件を gate が実際に見るようにした**（下の 3）
2. **許諾の回答メールを Gmail 内で探した → 0件**（下の 1）
3. **`scripts/account_audit.py` を新設し、チャンネルを実測した**（下の 2）
4. **素材候補を洗い直し、自動判定の穴を1つ塞いだ**（下の 4）
5. `M7ZxIL_b39E` から12候補を抽出、上位8本の書き出しを開始（**未完**）

変更したファイル:
`clipper/gate.py` / `clipper/cli.py` / `config/settings.yaml` / `config/permission.yaml` /
`config/exclusions.yaml` / `tests/test_gate.py` / `scripts/account_audit.py`（新規）/
`scripts/build_source_pool.py` / `docs/permission-request.md` /
`docs/analytics-2026-09-04.md`（新規）/ `HANDOFF.md`

コミット: `00d10e3`（gate の収益化条件）、`1068c69`（実測と素材の洗い直し）。
どちらも `origin/main` へ push 済み。**本体チェックアウト側の main は古いので `git pull` が要る。**

## 検証済みの事実（実際に画面に出た出力だけ）

### 1. 許諾の回答メールは受信箱に無い

`status: granted` の根拠になるはずの回答文を Gmail（`oshima6.27@gmail.com`）で探した。

| クエリ | 結果 |
|---|---|
| `BRDOCK OR brdc OR コムドット newer_than:60d` | **0件** |
| `{BRDOCK brdc コムドット 切り抜き やまと 名場面} in:anywhere newer_than:120d` | 6件（**BRDOCK 由来は0件**） |

6件はひろゆき切り抜きの申請（`getmcn@razil.jp`、別プロジェクト）と Adobe の宣伝。
`in:anywhere` なので迷惑メール・ゴミ箱も見ている。
**株式会社BRDOCK からのメールは自動返信も含めて1通も無い。**

**これは「許諾が無い」の証明ではない。**「この受信箱には残っていない」だけ。
別アドレス・電話・フォーム画面上の回答・削除の可能性は残る。
**`status` は運営者の判断が要るので変更していない。**
経緯は [`docs/permission-request.md`](docs/permission-request.md)。

### 2. アカウントの実測（`python scripts/account_audit.py`）

| 項目 | 値 |
|---|---:|
| 登録者 | **0** |
| アップロード済み | **34本**（公開 16 / 非公開 18） |
| 公開分の再生 | 合計 60 / 中央値 4 / 最大 10 |

**台帳との突き合わせは34本すべて一致。** 紐づかない動画は無い。

| 公開時期 | 本数 | 再生/日 の平均 |
|---|---:|---:|
| 2026-08-18〜08-22 | 14 | **0.22** |
| 2026-09-02（再開後） | 2 | **3.75** |

**17倍という比をそのまま信じないこと。** ショートは公開直後に再生が集中するので、
2日目の動画が再生/日で有利になるのは当たり前。8月分の「最初の2日」の数字は無く、
**同じ土俵の比較になっていない。**

比に頼らない事実が1つある。**9月の2本は2日で8回・7回に達しており、
8月14本のうち13本の「17日かけた合計」を超えている**（8月の最高は10回）。

素材ごとの1本あたり再生は `RGm5F2m12as` 7.5 → `8DDHTuwdbyQ` 6.5 → `abW8zkEwEW4` 4.7 →
… → `wKuTNfA6Xhg` 0.0。**この順位を制作の根拠にしない。** 母数が60再生で1回の差が順位を動かす。
**1位の `RGm5F2m12as` は除外済みの素材で、公開中の2本は削除予定**（下の「次にやること 3」）。

詳細は [`docs/analytics-2026-09-04.md`](docs/analytics-2026-09-04.md)。

### 3. 収益化の許諾条件を gate が見るようにした

`permission.yaml` には「conditions を gate が読んで判定する」と書いてあったが、
**gate は `status` しか見ておらず conditions は誰も読んでいなかった。注記が誤りだった。**

- `config/settings.yaml` に `channel.monetization_enabled`（既定 `false`）を追加。
  **API では取れないので Studio を見て手で書く欄**
- `monetization_enabled: true` かつ `conditions.monetization` が `allowed` 以外なら held

実際の設定・実際の台帳で `gate.evaluate` を動かした出力:

```
収益化 ON  : {'result': 'held', 'reasons': ['チャンネルが収益化されているが、許諾の収益化条件が unknown（allowed ではない）']}
収益化 OFF : {'result': 'pass', 'reasons': []}
```

**収益化していないうちは `unknown` でも通す。** 止めたいのは「許諾の範囲を超えて
収益を得ること」であって投稿そのものではない。全部止めても安全にはならず在庫が止まるだけ。

**`credit_required` / `member_images_allowed` / `excluded_video_types` はまだ誰も読んでいない。**

### 4. 素材候補を洗い直し、自動判定の穴を塞いだ

`python scripts/build_source_pool.py 60` で通ったのは4本。中身まで見て判定した:

| id | 尺 | 判定 |
|---|---|---|
| `M7ZxIL_b39E` マクドナルド過注文人狼（09-02、100万再生） | 1:21:06 | **候補**。最新・最大再生。**ただし店内撮影で客と店員の映り込みが濃厚** |
| `fDiW0YbLd-Q` 限界酒ゆうた（07-20、98万再生） | 1:19:31 | 保留。第三者リスクは低いが**全編が飲酒。年齢制限が付くとフィードに出ない** |
| `lCKD3eRA6nE` 命の燃やし方 密着 | 3:46:51 | **除外**（外部の方「金吾」、書籍・イベント関係者） |
| `zvM7bkbavDQ` コトダマMV密着 | 2:13:47 | **除外**（概要欄に「出演してくれたファンのみんな」） |

`zvM7bkbavDQ` は**概要欄にファン参加と書いてあるのに素通りした。**
`description_patterns` が `出演してくれたクリエイター` とクリエイター限定だったのが穴。
`出演してくれた` に広げた。実行して確認:

```
zvM7bkbavDQ  ok=False  ['概要欄に除外語『出演してくれた』を含む']
lCKD3eRA6nE  ok=False  ['exclusions.yaml の video_ids に登録されている']
M7ZxIL_b39E  ok=True
fDiW0YbLd-Q  ok=True
```

`build_source_pool.py` が worktree で落ちていたのも直した（`work/` を作らずに書き込んでいた）。

### 5. テスト

```
$ python -m pytest tests/ -q
148 passed, 4 warnings in 0.94s
```

`tests/test_gate.py` に収益化条件の6件を追加した。
**設定ファイルの現在値ではなく、ゲートの挙動を monkeypatch で固定している。**

## 未検証のもの

- **許諾の回答文を見ていない。** `granted` の根拠は運営者の申告だけで、
  Gmail を探しても裏づけは出なかった（上の 1）
- **`M7ZxIL_b39E` は1コマも見ていない。** 店内撮影なので
  `fbKne9hTmgA`（体育館の一般の方）と同じ落ち方をしうる。**採否は未定**
- **投稿再開でインプレッションが増えるかは未検証。** 09-09 に測るまで分からない
- **書き出した全クリップを通しで再生していない。** 見たのは各1〜3コマ
- **アップロード済み6本のタイトルは旧型式**（メンバー名・`#shorts` なし）
- **新環境で実際のアップロード・公開を1本も通していない。**
  `clipper auth` がチャンネルを返すところまで
- **新しいトークンが7日後も生きているかは未検証。** 本番環境で取り直したので
  失効しない見込みだが、**2026-09-10 を過ぎるまで実証できない**
- **クォータの実際の上限を確認していない。** 既定なら 10,000ユニット/日
- `fDiW0YbLd-Q` の飲酒が年齢制限を受けるかは未確認
- **`G2gXaVSnOQY`（北海道前編）は未着手。** すすきの回なので第三者リスクが高い

## 次にやること

**すべて `Set-Location` と環境変数を先に打つこと**（PowerShell 5.1。`&&` は使えない）:

```powershell
Set-Location C:/Users/oshim/Documents/projects/com.-youtube
$env:CLIPPER_CREDENTIALS_DIR = "C:/Users/oshim/Documents/projects/com.-youtube"
```

### 0. `M7ZxIL_b39E` の書き出しを終わらせ、**コマを見てから採否を決める**

書き出しが auto01 の1本で止まっている。続きから:

```powershell
python -m clipper run M7ZxIL_b39E --count 12 --render 8
python scripts/audit_third_parties.py M7ZxIL_b39E
```

点検シートは `work/M7ZxIL_b39E/<clip_id>_audit.png`。
**マクドナルド店内なので、客・店員が特定できる形で映っていたらその区間は捨てる。**
全部だめなら動画ごと `exclusions.yaml` の `video_ids` へ理由付きで足す。

抽出済みの12候補（スコア上位は `auto01` 67.9 / `auto02` 53.0 / `auto03` 46.4）:

| clip | 区間 | clip | 区間 |
|---|---|---|---|
| `auto01` | 1:08:53-1:09:58 | `auto07` | 0:47:45-0:48:46 |
| `auto02` | 0:25:51-0:26:57 | `auto08` | 1:02:30-1:03:37 |
| `auto03` | 0:30:39-0:31:46 | `auto09` | 0:24:29-0:25:35 |
| `auto04` | 0:00:00-0:01:04 | `auto10` | 0:28:16-0:29:24 |
| `auto05` | 0:01:29-0:02:34 | `auto11` | 1:18:40-1:19:42 |
| `auto06` | 1:14:39-1:15:44 | `auto12` | 0:10:09-0:11:15 |

### 1. 許諾の回答文を突き止める（**優先度が最も高い**）

Gmail に無かった（上の 1）。運営者が確かめること:

1. **回答はどこに来たのか。** 別アドレス / 電話 / フォームの画面上 / SNS。
   **来ていないなら `permission.yaml` の `status` を `pending` に戻す**
2. 出てきたら `docs/permission-request.md` に貼り、条件を `conditions` へ書き写す
3. **とくに `monetization`。** `allowed` にしない限り、収益化した時点で gate が全部止める

回答が出てこないなら**送り直すのが筋**。依頼文は `docs/permission-request.md` にそのまま残っている。

### 2. インプレッションを測り直す（2026-09-09 ごろ）

Studio → アナリティクス → 右上「詳細モード」。**355回から動いたかを見る。**
再生数ではなく**配信側の数字**で見ること。動かなければ投稿頻度は原因ではなかったということ。

### 3. 除外2本を削除する（Studio で手動。**取り消せない**）

`cTzbNUFi9Iw` と `hbRhnrvPk-k`。素材 `RGm5F2m12as` 由来で外部の催眠術師が映る。
**現在も公開されていて、しかもチャンネルで最も見られている2本**（10回・5回）。

### 4. 在庫18本の投稿を続ける

計画は `config/schedule.yaml`（18枠）。先頭は `Gsd-7b4Kdx8/auto05` と `Gsd-7b4Kdx8/auto01`。

```powershell
python -m clipper schedule            # 計画を見るだけ
python -m clipper schedule --arm      # 実際に予約を入れる
python -m clipper publish Gsd-7b4Kdx8 auto05   # 手で出す
```

計画を組み直すときは `python scripts/build_schedule.py [開始日] [1日の本数]`。

### 5. トークンが生きているかを時々見る（1ユニット）

```powershell
python -m clipper auth
```

チャンネル名と `UCoT2TYsxzH4t42C2oF-KrAw` が出れば生きている。
切れていたら `token.json` を消して同じコマンド（同意画面では
**「コムドット名場面ch【切り抜き】」を選ぶ**。ブランドアカウント名は
「コムドットのおもしろ切り抜きチャンネル」で**チャンネル名と違う**ので名前で探すと迷う）。
**2026-09-10 を過ぎても生きていれば、7日失効が無いことの実証になる。**

### 6. 旧型式のタイトル6本を直す

```powershell
python -m clipper retitle <video_id> <clip_id> --title "<本文>" --members <確認した名前>
```

50ユニット／本。**動画IDも再生数も維持される。**
`cTzbNUFi9Iw` / `hbRhnrvPk-k` は削除予定なので直さない。

## 触ってはいけないところ

### 権利

- **コラボ回・ファン参加回・イベント回は第三者の肖像の問題で使えない。**
  許諾を依頼したのは BRDOCK だけで、第三者はその射程外
- **`--members` に推測を渡さない。** 映像で確認したものだけ。名簿外は弾かれるが、
  **名簿内の別人の名前は弾けない**
- **自動判定を通っても使えるとは限らない。** 画面に誰が映っているかはタイトルにも
  概要欄にも出ない。**実測で4回外している**（`fbKne9hTmgA` 体育館の一般の方 /
  `MgO0lCUtlx4 auto01` 高校対中学の試合 / `RGm5F2m12as` 外部の催眠術師 /
  `zvM7bkbavDQ` ファン参加）。**書き出したら必ず `audit_third_parties.py` でコマを見る**
- 動画ごと除外: `RGm5F2m12as` / `fbKne9hTmgA` / `ARuwTdvqJJA` / `lCKD3eRA6nE`
- `Fb9bO8V9oNA`（目隠しかくれんぼ）は CDF シャッフルコラボ回。素材にしない
- `abW8zkEwEW4/auto03` は下ネタのため素材にしない

### 運用

- **`clipper schedule --rebuild` を打たない。** `config/schedule.yaml` の `slots` は
  「2026-08-18 に Studio で実際に入っていた予約の写し」という記録で、上書きすると消える。
  投稿順は `scripts/week_plan.py`（`docs/post-plan.md`）で出す
- **1日の公開は2本まで**（`settings.yaml` の `max_publish_per_day`）。gate が数えている。
  なお gate の当日上限は**スロットの日付ではなく「今日」の公開本数**を見るので、
  今日2本出したあとは未来日付のスロットまで巻き添えで止まる。
  **公開を増やすために安全弁を緩める変更は勝手に入れない**
- カスタムサムネイル不可・15分超不可（電話番号確認ができないため）。**再依頼しない**

### 認証とリポジトリ

- **`token.json` / `client_secret.json` を退避するとき、リポジトリ内に置かない。**
  `.gitignore` は `token.json*` などに広げたが、**別名（例: `auth_backup.json`）にすれば
  素通りする**。退避先はリポジトリの外にすること
- **このリポジトリは PUBLIC。** `git add -A` の前に `git status --short` で中身を見る
- 端末は **Windows PowerShell 5.1**。`VAR=値 コマンド` と `&&` はどちらも使えない
  （`&&` はパースエラーで**行ごと何も実行されない**）。環境変数は `$env:NAME = "値"` を
  別行で、逐次実行は `;` でつなぐ。**Claude 側の Bash ツールは Git Bash なので書き分けること**
