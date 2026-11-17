# CHANGELOG

このファイルは **エンジン本体**（`engine/`・`tools/` とそのドキュメント）のリリースノート。
キャンペーンごとの開示ログ（`campaigns/<name>/CHANGELOG.md`、書式は
[engine/changelog.spec.md](engine/changelog.spec.md)）とは別物。

書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、番号付けは
[Semantic Versioning](https://semver.org/lang/ja/) に従う。現行バージョンは [VERSION](VERSION)。

## バージョン番号の決め方

このエンジンの「公開インターフェース」は、キャンペーンが依存するデータ形式と手順である。

| 上げる桁 | 条件 | 例 |
|----------|------|----|
| **MAJOR** (X.0.0) | 既存のキャンペーンがそのままでは使えなくなる変更 | `facts/`・`state.yaml` の項目の削除・改名・意味変更 / `JOURNAL.md` の見出し構成の変更 / 既存のセーブが新たに FAIL する監査の追加 / セーブ時スナップショットの書式変更 |
| **MINOR** (0.Y.0) | 既存のキャンペーンを壊さない追加 | 任意項目の追加 / 新しい `engine/` 文書 / 既存のセーブを落とさないチェックの追加 |
| **PATCH** (0.0.Z) | 挙動を変えない修正 | 誤字・文言の明確化 / ゲート（`tools/export_gate.py`）の誤判定の修正 |

MAJOR を上げるリリースには、移行手順（既存キャンペーンの何をどう書き換えるか）を必ず添える。

## [Unreleased]

## [1.1.0] - 2026-11-18

開幕の仕方と、毎手の処理を機構で決める仕組みを追加。既存のキャンペーンはそのまま動く（新しい検査は、新しいファイルがあるときだけ働く）。

### 変更

- 開始プロトコル 条件4: 一手目を「見渡し手」にした。到着の場面から始め、見回せる場所・人・物を置き、急がせない。
  事件の有無は一手目から抽選で決め、一手目は小イベントまで（[engine/OPENING_PROTOCOL.md](engine/OPENING_PROTOCOL.md)）。
  旧版の「一手目でいきなりイベントを起こす」は廃止。
- `state.yaml` の `npcs` の推奨項目を `{ id, regard, cares, area, spot, alive }` に変更。
  旧項目（`disposition` / `location`）でもゲートは落ちないが非推奨。反応の機構を使うなら新項目へ移す。

### 追加

- イベント抽選: GM の応答ごとに d20＋緊張度で、平穏／小イベント／大イベントを決める。出目は GM ではなく
  `tools/draw.py` か player が渡す乱数列から取る。事件の中身は `world/04_events.md` の事件プールから選ぶ
  （[engine/event_draw.md](engine/event_draw.md)）。
- 手番ログ `TURNLOG.md`: 手ごとに入力・行為・判定・抽選・事件・起きたこと・反応・目撃・噂・新設定・台帳・開示の
  12 キーを記録する。`npc:` / `fact:` / `ev:` / `rumor:` の id 参照で検索できる（`tools/turnlog.py`、
  [engine/turnlog.spec.md](engine/turnlog.spec.md)）。
- 反応の機構: NPC の態度（regard −3〜+3 と cares）、噂の発生と伝播、行動の成否を、行為タグの表と出目で決める
  （`tools/roll.py`、[engine/reaction.md](engine/reaction.md)）。好感の帯が NPC の振る舞いと、
  NPC の発話による開示の上限を縛る。
- 新設定の書き戻し: 本文や台詞で口にした新しい設定を同じ手で `world/` に書き戻し、`CANON+` として記録する。
- 生ログ `TRANSCRIPT.md`: 手ごとに入力と本文を原文のまま残し、TURNLOG と手番で対応づける
  （[engine/transcript.spec.md](engine/transcript.spec.md)）。
- GM 契約に第9条（手番ログ）・第10条（反応は表と出目で決め、新設定は書き戻す）。
- ゲート（Python 版）に検査 L〜S。TURNLOG.md / TRANSCRIPT.md があるときだけ働く。
  - L 手番連続 / M 抽選照合 / N 参照実在 / O キー欠落
  - P 新設定 / Q 好感照合 / R 噂 / S 生ログ対応
- エンジン作業ログ `WORKLOG.md` と、git 履歴との突き合わせ `tools/worklog_sync.py`。
- テンプレート: `TURNLOG.md`・`TRANSCRIPT.md` を追加し、`state.yaml` の meta（move / tension / last_major_move）と
  `world/04_events.md`（事件プールの書式）を更新。

### 既知の制限

- コード無し版の監査（`engine/AUDIT_PROTOCOL.md`）には、L〜S 相当の手順をまだ足していない。
- 行為タグ・難易度への分類と、書き戻した新設定が既存設定と意味として矛盾しないかは、機械では検査できない。

## [1.0.0] - 2026-10-30

初回公開。

### 含まれるもの

- 三層開示: `facts/*.yaml`（Canon / Revealed / Belief）と、開示操作 `REVEAL` / `DISINFO` / `CORRECT`
- 物質台帳: `state.yaml`（収支履歴からの残高導出、価格表参照）
- GM契約、開始プロトコル（セッションゼロ・一手目イベント）、季節注入
- 進行メモ: `JOURNAL.md`（現在地と経緯。セッションをまたいで続きから再開する。
  [engine/journal.spec.md](engine/journal.spec.md)）
- export gate: コード無し版（`engine/AUDIT_PROTOCOL.md`）と Python 版（`tools/export_gate.py`）。
  開示5チェック（A〜E）と台帳6チェック（F〜K）
- コード不要で始める起動プロンプト（[START_HERE.md](START_HERE.md)）
- 空のキャンペーン雛形（`campaigns/_template/`）
