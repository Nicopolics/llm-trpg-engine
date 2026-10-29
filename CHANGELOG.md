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
