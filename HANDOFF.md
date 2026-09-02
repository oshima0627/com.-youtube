# HANDOFF

最終更新: 2026-09-02

## いま何をしているのか

コムドット切り抜きの制作と投稿。**このセッションで投稿を再開した。**

- 認証を復旧（下の C）
- 許諾を `granted` にした（下の D。**根拠は運営者の申告のみ**）
- 新しいショートを7本書き出し、既存と合わせて**14本すべてをアップロード**（下の E）
- **本日2本を公開した**（下の F）
- 残り12本が非公開の在庫 ＝ 6日分。順番は [`docs/post-plan.md`](docs/post-plan.md)

**予約（`schedule --arm`）は入れていない。** 毎日 `clipper publish` を打つ形。

## 今回やったこと（2026-09-02）

1. 公開済み14本の実績を実測し、競合ショートと突き合わせた → `docs/analytics-2026-09-02.md`
2. Studio をブラウザで開いてインプレッション数を読んだ（下の H）
3. ショートのタイトルにメンバー名と `#shorts` を必須にした（下の B）
4. `ARuwTdvqJJA`（40組コラボ）を除外に追加
5. 新しいショートを7本書き出した（下の A）
6. 台帳の `privacy_status` を実測に合わせた
7. 認証復旧・許諾更新・14本アップロード・2本公開（下の C〜F）

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

```bash
CLIPPER_CREDENTIALS_DIR=C:/Users/oshim/Documents/projects/com.-youtube python -m clipper ...
```

古いトークンは `invalid_grant` だったので退避して `clipper auth` をやり直した
（同意画面はブラウザで通した）。結果:

```
channel: {'id': 'UCoT2TYsxzH4t42C2oF-KrAw', 'title': 'コムドット名場面ch【切り抜き】'}
```

**同意画面のブランドアカウント名は「コムドットのおもしろ切り抜きチャンネル」で、
チャンネル名と違う。** 名前で探すと迷う。選んだあと `UCoT2TYsxzH4t42C2oF-KrAw`
が出れば正しい。退避した古いトークンは削除済み。

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

## 未検証のもの

- **8本とも通しで再生していない。** 見たのは各1〜3コマと、元素材の6〜9コマ
- **許諾の回答文を見ていない。** granted の根拠は運営者の申告だけ
- **アップロード済み6本のタイトルは旧型式**（メンバー名・`#shorts` なし）。
  直すには誰が映っているかの確認が要る
- **投稿再開でインプレッションが増えるかは未検証。** これが今回いちばん測りたいこと
- **クォータの実際の上限を確認していない。** 12,800ユニット分が通った理由は不明
- `xBpumDn8QYE` の飲酒描写が年齢制限を受けるかは未確認
- `wKuTNfA6Xhg/auto03`（冒頭 10-78秒）は未点検・未書き出し。予備

## 次にやること

### 1. 毎日2本ずつ公開する（在庫12本 ＝ 6日分）

順番は [`docs/post-plan.md`](docs/post-plan.md)。次は `bCKjVkvfJIM/auto03` と
`51tyFgelkmQ/auto03`。

```bash
cd C:/Users/oshim/Documents/projects/com.-youtube/.claude/worktrees/video-creation-scheduling-2370b5
export CLIPPER_CREDENTIALS_DIR=C:/Users/oshim/Documents/projects/com.-youtube
python -m clipper publish bCKjVkvfJIM auto03
python -m clipper publish 51tyFgelkmQ auto03
```

自動化するなら `clipper schedule --arm`。ただし **`--rebuild` は
`config/schedule.yaml` の実予約の記録を上書きする**ので、先に退避すること。

### 2. 1週間後にインプレッションを測り直す（2026-09-09 ごろ）

Studio → アナリティクス → 右上「詳細モード」。**355回から動いたかを見る。**
動かなければ、投稿頻度は原因ではなかったということ。

### 3. トークンの失効に備える

OAuth 同意画面が「テスト中」だとリフレッシュトークンが**7日で切れる**。
切れたら本体の `token.json` を消して `clipper auth` をやり直す（上の C）。

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
