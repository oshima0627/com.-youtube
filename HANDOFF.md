# HANDOFF

最終更新: 2026-09-02

## いま何をしているのか

コムドット切り抜きの制作。**このセッションで1週間分（14本・2本/日）の在庫が揃った。**
内訳は書き出し済み8本＋アップロード済み（非公開）6本。投稿順は
[`docs/post-plan.md`](docs/post-plan.md)。

**ただし1本も投稿していない。できない。** 理由は下の E。
**予約も入れていない。**

## 今回やったこと（2026-09-02）

1. 公開済み14本の再生数を実測し、競合ショートと突き合わせた → `docs/analytics-2026-09-02.md`
2. ショートのタイトルにメンバー名と `#shorts` を必須にした（下の C）
3. `@comdot` の新着を調べ、`ARuwTdvqJJA` を除外に追加（下の D）
4. **新しいショートを7本書き出した**（下の B）
5. 台帳の `privacy_status` を実測に合わせた（14件が private → public）
6. 投稿順の表を作る `scripts/week_plan.py` を追加
7. **YouTube Studio をブラウザで開いてインプレッション数を読んだ**（下の G）

変更したファイル:
`clipper/metadata.py` / `clipper/upload.py` / `clipper/cli.py` /
`config/exclusions.yaml` / `data/videos/*.json` /
`docs/analytics-2026-09-02.md`（新規）/ `docs/post-plan.md`（新規）/
`scripts/week_plan.py`・`scripts/sync_privacy.py`・`scripts/sheet_at.py`（新規）/
`tests/test_metadata.py`（新規）/ `tests/test_upload.py` / `README.md` / `HANDOFF.md`

## 検証済みの事実（実際に画面に出た出力のみ）

### A. 在庫はちょうど1週間分

```
$ python scripts/week_plan.py 2026-09-03 2
在庫 14本 = 7.0日分。
```

`out/` の8本を実測（すべて 1080x1920 h264、57.0〜67.9秒）:

```
8DDHTuwdbyQ_auto03_short.mp4   66.55s  14.5MB
8DDHTuwdbyQ_auto05_short.mp4   60.45s  12.2MB
8DDHTuwdbyQ_man01_short.mp4    67.90s  14.4MB
abW8zkEwEW4_auto04_short.mp4   67.32s  22.1MB
abW8zkEwEW4_auto05_short.mp4   62.93s  21.1MB
abW8zkEwEW4_auto06_short.mp4   66.48s  20.1MB
xBpumDn8QYE_man01_short.mp4    57.00s  43.6MB
xBpumDn8QYE_man02_short.mp4    61.60s  12.8MB
```

残り6本はアップロード済み（非公開）。yt-dlp で `Private video` を確認済み:
`0gWpS9XyIEs` / `CCb0ZcuhoZA` / `MDPhcHIYOL8` / `TjovR5KnSu4` / `tUyrCoVoPCM` / `jr9NXY7P8dk`

### B. 新しく書き出した7本は全部、第三者点検を通してある

| クリップ | 区間 | 場所と人 |
|---|---|---|
| `xBpumDn8QYE/man02` | 1:32:20-1:33:22 | 座敷。**メンバー2人だけ**（8コマ目視） |
| `8DDHTuwdbyQ/auto03` | 57:44-58:51 | 座敷。**4人だけ**（6コマ目視） |
| `8DDHTuwdbyQ/auto05` | 1:02:45-1:03:46 | 同上（6コマ目視） |
| `8DDHTuwdbyQ/man01` | 1:06:11-1:07:19 | 同上（6コマ目視） |
| `abW8zkEwEW4/auto06` | 1:15-2:22 | ソファ。**5人だけ**（9コマ目視） |
| `abW8zkEwEW4/auto04` | 37:33-38:40 | 車内。**2人だけ**（6コマ目視） |
| `abW8zkEwEW4/auto05` | 1:20:27-1:21:30 | 室内。**5人だけ**（6コマ目視） |

- `8DDHTuwdbyQ` は「やまとの誕生日パーティーをやまと抜きで」の回。
  **画面には4人しかいない＝やまと以外の4人**というのがメンバー特定の根拠
- `abW8zkEwEW4/auto06` には LINE 画面のオーバーレイが出るが、
  拡大して確認したところ**写っているのはメンバー本人の写真とアイコン**（じろう＝ゆうた）
- 点検シートは `work/<video_id>/<clip_id>_audit.png`（git 追跡外）

**`8DDHTuwdbyQ/auto04` は捨てた。** 冒頭の焼き込みテロップが
「知ってるよね？雷獣チャンネル」で、見出しと合わなかった。
`man01`（1:06:11 始まり＝「いよいよラストのトークテーマです」）に切り直した。
台帳の auto04 には理由を書いて `excluded` にしてある。

**採らなかったもの**: `abW8zkEwEW4/auto03`（54:44-55:50）。
キス・攻めの下ネタが続く区間のため素材にしない。

### C. ショートのタイトルの型を機械の検査にした

原因は「docs に書いてあるだけで `short_title()` がどこからも呼ばれていなかった」。

- `SHORT_TAGS` = `#コムドット #コムドット切り抜き #shorts`
- `short_title(body, members)` がメンバータグを組み立て、名簿
  `metadata.MEMBERS`（やまと/ゆうた/ゆうま/ひゅうが/あむぎり）外を弾く
- 100文字超は**末尾のタグを丸ごと落とす**（途中で切らない）
- `validate_title(title, is_short=True)` が `#shorts` とメンバー名を**必須**にする
- CLI に `--members` と **`retitle` サブコマンド**を追加

```
$ python -m pytest -q
140 passed, 4 warnings in 1.03s
```

**`--members` は映像で確認できたメンバーだけ。** 字幕からは決められない
（公開済みショート19本のうち16本は区間内の字幕に名前が1つも出ない）。

### D. 新着で使える素材が無い

| 動画 | 判定 |
|---|---|
| `ARuwTdvqJJA`（08-28） | **除外**。概要欄に「総勢40組のクリエイターに借りていただきました」「コラボ動画を撮影する」 |
| `tvpzuKIW71o` / `2Ip54dw8F_M` | メンバーシップ限定。`screen()` が弾く |
| `xBpumDn8QYE`（08-26） | 使える。今回 man02 を切った |

`ARuwTdvqJJA` は自動判定を素通りしていた（`ok=True` を確認）。
`config/exclusions.yaml` に video_id と `コラボ動画` パターンを足した。

### E. 投稿はできない（2つとも実行して確認）

**E-1. このワークツリーに認証情報が無い。**

```
$ python -m clipper upload xBpumDn8QYE man02 --title "..." --members ひゅうが,ゆうま
× client_secret.json がありません。
```

`client_secret.json` / `token.json` は本体
`C:/Users/oshim/Documents/projects/com.-youtube` にしかなく、`token.json` は
2026-08-14 のまま（記録では `invalid_grant`）。

**E-2. 許諾が pending なので gate が止める。** 今回の7本すべて:

```
gate: held ['許諾ステータスが pending（granted ではない）']
```

依頼文で「ご許諾をいただけた場合にのみ公開いたします」と伝えている。
**gate を迂回する形での公開・予約はしていない。**

### F. 露出がほぼ出ていない（作る前の問題）

公開済み14本の**合計再生45回**、ショート中央値3回。競合の中央値は
29,500〜159,000で、一番伸びなかった1本でも2,900回。
**在庫を増やしても、この差は埋まらない。** 詳細は `docs/analytics-2026-09-02.md`。

### G. Studio で原因の側が確定した（2026-09-02、画面で確認）

**API は失効したままなので、ブラウザで Studio を開いて読んだ。**
期間 2026/08/04〜08/31。

| 指標 | 値 |
|---|---:|
| 視聴回数 | 45 |
| チャンネル登録者 | **0** |
| **サムネイルのインプレッション数** | **355**（14本・28日。1本あたり25回） |
| サムネイルのクリック率 | 1.4% |

**視聴者がショートを見つけた方法**

```
YouTube 検索        86.4%
直接入力または不明   6.8%
ショート フィード    4.6%   ← 45回の4.6% ＝ およそ2回
ブラウジング機能     2.3%
```

**視聴者のエンゲージメント**

```
視聴を継続 60.0%  /  スワイプして消去 40.0%
```

ショート一覧の「通知」列は全13本が「–」。**制限も著作権の申し立ても無い。**

**結論: 止まっているのは配信で、中身でも設定でもない。**
前回の引き継ぎに「インプレッションが二桁以下なら配信されていない。
作り方の調整では動かない」と書いた条件に**該当した。**

- 1本25回のインプレッションでは、良し悪しを判定する母数にならない
- 出た分の**6割は見続けている**。中身が拒否されているのではない
- **尺・タイトル・切り抜き地点をいじっても、この数字は動かない**

## 未検証のもの

- **8本とも通しで再生していない。** 見たのは各1〜3コマと、元素材の6〜9コマ
- **アップロード済み6本のタイトルは旧型式のまま**（メンバー名・`#shorts` なし）。
  直すには誰が映っているかの確認と API 復旧の両方が要る
- **タイトルの型を直せば伸びるかは未検証。** 露出がゼロに近く効果を測れない
- **`xBpumDn8QYE` の飲酒描写が年齢制限を受けるかは未確認**
- `wKuTNfA6Xhg/auto03`（冒頭 10-78秒）は未点検・未書き出し。予備

## 次にやること

### 1. 書き出した8本を通しで見て、出すものを決める（人）

```bash
start "" "C:\Users\oshim\Documents\projects\com.-youtube\.claude\worktrees\video-creation-scheduling-2370b5\out"
```

### 2. API を復旧する（人がブラウザで行う）

```bash
cd C:/Users/oshim/Documents/projects/com.-youtube && rm token.json && python -m clipper auth
```

同意画面では「コムドット名場面ch【切り抜き】」を選ぶ。`UCoT2TYsxzH4t42C2oF-KrAw`
が表示されれば正しい。**7日でまた失効する。**

### 3. 8本を非公開でアップロードする（**本体側から**。公開はしない）

```bash
cd C:/Users/oshim/Documents/projects/com.-youtube
python -m clipper upload 8DDHTuwdbyQ auto03 --title "渾身のパンチラインを一番気持ちよく喰らってくれるのがやまとなのが良すぎる" --members あむぎり,ゆうた
python -m clipper upload 8DDHTuwdbyQ auto05 --title "売れても戻ってきたら前のままなやまとの話が良すぎる" --members ゆうた,あむぎり
python -m clipper upload 8DDHTuwdbyQ man01  --title "最後のトークテーマが『28歳のやまとに期待すること』なのが良すぎる" --members ゆうた,あむぎり
python -m clipper upload abW8zkEwEW4 auto06 --title "5人のLINEグループで2人しか喋っていないことが発覚するのが面白すぎる" --members ひゅうが,ゆうた
python -m clipper upload abW8zkEwEW4 auto04 --title "自信作を出す直前にじゃんけんで順番を決めだすのが面白すぎる" --members ゆうた
python -m clipper upload abW8zkEwEW4 auto05 --title "食べた瞬間『何これ美味い』しか言えなくなるのが面白すぎる" --members ゆうま,ひゅうが
python -m clipper upload xBpumDn8QYE man01  --title "酔い潰れた相方を抱え上げたら完成した画が面白すぎる" --members ひゅうが,ゆうま
python -m clipper upload xBpumDn8QYE man02  --title "『成功だけが幸せじゃない』で締める北海道旅行が良すぎる" --members ひゅうが,ゆうま
```

`videos.insert` は1本1,600ユニット。**1日6本が上限**なので2日に分ける。

### 4. 除外2本を削除する（Studio で手動）

`cTzbNUFi9Iw` と `hbRhnrvPk-k`。素材 `RGm5F2m12as` 由来で外部の催眠術師が映る。
**この2本は現在も公開されている**（今回の実測で確認）。

### 5. 許諾の扱いを決める

`config/permission.yaml` は `pending` のまま、14本が公開中。
依頼文は「ご許諾をいただけた場合にのみ公開いたします」。
**依頼を本当に送ったのかを確認する。** `granted` にしない限り
`clipper publish` も `clipper schedule --arm` も通らない。

### 6. 公開済み13本のタイトルを直す（メンバー名 + `#shorts`）

```bash
python -m clipper retitle <video_id> <clip_id> --title "<本文>" --members <確認した名前>
```

`retitle` は50ユニット／本。**動画IDも再生数も維持される。**
`cTzbNUFi9Iw` / `hbRhnrvPk-k` は削除予定なので直さない。

### 7. （済）Studio でインプレッション数を確認した

→ 上の G。**配信されていない側だった。**
次に確かめる価値があるのは「なぜ配信されないのか」で、
測れていないのは以下。**どれも未検証の仮説として扱うこと。**

- 08-22 以降**11日間投稿が止まっている**。新規投稿が無ければフィードの試行も無い
- 登録者0・履歴なしの新規チャンネルに割り当てられる試行枠がそもそも小さい
- 先行プロジェクト tora-kirinuki も**同じ症状で原因未特定**
  （公開8本・総再生4回・登録者0。`docs/findings-from-tora-kirinuki.md`）

## 触ってはいけないところ

- **gate を迂回して publishAt を入れない。** `permission.yaml` が `granted` に
  なるまで `schedule --arm` を打たない。Studio での手動予約も運営者の判断領域
- **`clipper schedule --rebuild` を打たない。** `config/schedule.yaml` の `slots` は
  「2026-08-18 に Studio で実際に入っていた予約の写し」という記録で、上書きすると消える。
  投稿順は `scripts/week_plan.py`（`docs/post-plan.md`）で出す
- **`--members` に推測を渡さない。** 映像で確認したものだけ。名簿外は弾かれるが、
  **名簿内の別人の名前は弾けない**
- `RGm5F2m12as` / `fbKne9hTmgA` / `ARuwTdvqJJA` は動画ごと除外
- `Fb9bO8V9oNA`（目隠しかくれんぼ）は CDF シャッフルコラボ回。素材にしない
- `abW8zkEwEW4/auto03` は下ネタのため素材にしない
- カスタムサムネイル不可・15分超不可（電話番号確認ができないため）。再依頼しない
- **コラボ回・ファン参加回は第三者の肖像の問題で使えない。**
  `xBpumDn8QYE` の自動候補の上位はファン・通行人とのやり取りなので、
  そのまま書き出さない（man01/man02 は手で選び直したもの）
