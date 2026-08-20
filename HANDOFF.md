# HANDOFF

最終更新: 2026-08-20

## いま何をしているのか

コムドット切り抜きの在庫作りと予約管理。**BRDOCK への許諾依頼(2026-08-14)は回答待ちのまま。**
非公開アップロードで在庫を積み、公開・予約(publishAt)は gate が pending の間止める運用。
実際の予約は運営者が YouTube Studio で手動で入れている(2026-08-22 07:00 まで入っている)。

## 今回やったこと(2026-08-20)

新規クリップ6本を仕上げて非公開でアップロードした。videos.insert は1本1,600ユニットで
6本=9,600。**本日のクォータ(10,000)はほぼ使い切り。回復は JST 16〜17時ごろ。**

| クリップ | YouTube ID | 内容 |
|---|---|---|
| bCKjVkvfJIM auto03 | 0gWpS9XyIEs | 全部の組に入ってるのにお荷物説 |
| bCKjVkvfJIM auto04 | jr9NXY7P8dk | キレた直後に次の投票の心配をされる |
| bCKjVkvfJIM auto05 | TjovR5KnSu4 | 9位の票数が道端の木と同等といじられる |
| nZSBkNRFsDQ auto03 | MDPhcHIYOL8 | お題の食べ物をフライング |
| 51tyFgelkmQ auto03 | CCb0ZcuhoZA | わさび醤油のまさかの神お菓子 |
| 51tyFgelkmQ auto04 | tUyrCoVoPCM | 分厚くカットされたお菓子が無理ゲー |

- 全6本、`scripts/audit_third_parties.py` の点検シート(6コマ)で**メンバー以外の映り込みなしを目視確認済み**。シートは `work/<video_id>/<clip_id>_audit.png`
- hook/footer は焼き込みテロップで裏取りした(例: 51tyFgelkmQ auto03 は ASR では「言い張る」場面に読めたが、テロップは「まさかのタイミングで神お菓子を発見」で、本当に美味かった場面)
- アップロード先チャンネル一致を全件確認(コムドット名場面ch【切り抜き】)
- `config/schedule.yaml` の not_scheduled に6本+横型 XPx2y_vDWV8 の提案枠を追記(08-23〜08-26、1日2本の上限内)
- 除外2件を記録: MgO0lCUtlx4 auto03(auto01 と同じ高校対中学バスケ試合。スコアボードで確認)、
  fbKne9hTmgA auto01/02 は動画ごと exclusions.yaml 済みだったことを確認
- Fb9bO8V9oNA(目隠しかくれんぼ)は CDF シャッフルコラボ回。概要欄に「出演してくれたクリエイター」を
  含むため gate の description_patterns で止まることを確認。**素材にしない**

## 検証済みの事実

- 6本のアップロード成功ログ(URL・チャンネル名)は実際の実行出力で確認
- `python -m clipper schedule --arm` を実行 → **10/10 件が「許諾ステータスが pending」で保留**、
  予約 0 件(実出力で確認)。gate は設計どおり動いている
- 書き出しは 1080x1920、帯(hook/footer/ハンドル)が載っていることをフレーム抽出で確認

## 未検証のもの

- 新規6本の再生確認は YouTube 上ではしていない(ファイルのフレーム確認のみ)
- wKuTNfA6Xhg auto03(区間取得・点検済み、第三者なし)は**未書き出し・未アップロード**。
  クォータ都合で今日は見送り。次のセッションの1本目候補

## 次にやること

1. クォータ回復後(JST 16時以降)、wKuTNfA6Xhg auto03 を仕上げて上げる:
   `python work/finish_clip.py wKuTNfA6Xhg auto03`(HOOKS に追記要) → `python work/upload_batch.py` 相当
2. BRDOCK の返信を確認。granted になったら `config/permission.yaml` を書き換え →
   `python -m clipper schedule --arm` で予約が通るようになる
3. 新素材が要るなら screening.md の OK 残り: fDiW0YbLd-Q(ゆうた飲酒回)、zvM7bkbavDQ(MV制作密着。
   スタッフ映り込みリスクあり、点検必須)

## 触ってはいけないところ

- **gate を迂回して publishAt を入れない。** 依頼文で「ご許諾をいただけた場合にのみ公開」と
  伝えている。Studio での手動予約は運営者の判断領域
- RGm5F2m12as / fbKne9hTmgA は動画ごと除外(exclusions.yaml)。予約や一括操作に巻き込まないこと
  (非公開で残っている cTzbNUFi9Iw / hbRhnrvPk-k は削除が要る、と schedule.yaml の経緯メモにある)
- カスタムサムネイル不可・15分超不可(チャンネルの電話番号確認ができないため)。再依頼しない
