# TURNLOG 仕様 — 手番ごとの処理記録

## 解く問題

JOURNAL はセーブ時にしか書かれず、CHANGELOG は型付き操作しか載らない。その間にある
「この手で誰がどう反応したか」「誰が見ていたか」は、GM の記憶にしか残らなかった。
NPC の態度の変化や目撃は、数手後には忘れられ、同じ NPC が前と食い違う振る舞いをする
（ドリフト）。

対策は機構に埋める。**GM の応答 1 回ごとに、固定書式のエントリを 1 つ `TURNLOG.md` に追記する。**
人物・事実・事件は id で参照し、後から機械的に検索・照合できるようにする。

---

## 1. 位置づけ（他のログとの棲み分け）

| | TURNLOG.md | JOURNAL.md | CHANGELOG.md |
|---|---|---|---|
| 粒度 | 1手（GM の応答 1 回） | セーブ 1 回 | 操作 1 回 |
| 書く人・時 | GM が毎手 | GM がセーブ時 | GM・ツールが操作時 |
| 中身 | GM 側の処理記録（入力・抽選・反応・目撃） | player に表出した物語 | REVEAL / SPEND / DRAW 等の型付き操作 |
| Canon | 書かない（`fact:<id>` で参照のみ） | 書かない | 書かない |

- **正本ではない。** 数値・位置・開示度は state.yaml と facts/ が正。TURNLOG から状態を復元しない。
- JOURNAL の「経緯」は、前回セーブ以降の TURNLOG から player に見えた部分を抜き出して書く。

## 2. 書式（append-only）

```
### move <n> | <clock> | <場所>
- 入力: <player の入力。原文のまま>
- 行為: <行為タグ>→npc:<id> ; ...    ／ 誰にも向かない行動は「中立」（→ reaction.md §1.2）
- 判定: 自動 ／ <難易度> d20=<r> mod=<m> → 成功|失敗（→ reaction.md §3）
- 抽選: <calm|small|major> d20=<r> tension=<before>→<after>    ／ 抽選しない手は「なし（理由）」
- 事件: ev:<event_id>    ／ 無ければ「—」
- 起きたこと: <1〜3 文の要約。人物は npc:<id> で参照してよい>
- 反応: npc:<id> <タグ>×<cares> d6=<r> <前>→<後> ; npc:<id> 変化なし ...    ／ 無ければ「—」
- 目撃: npc:<id>, <名前の無い者は文章で>    ／ 無ければ「—」
- 噂: rumor:<id>（発生）; rumor:<id> reach <x>→<y>（伝播）    ／ 無ければ「—」
- 新設定: <file>: <要約> ; ...    ／ 無ければ「—」（→ reaction.md §4）
- 台帳: <その手で動いた state のキー>    ／ 無ければ「—」
- 開示: <REVEAL/DISINFO/CORRECT fact:<id> ...>    ／ 無ければ「—」
```

- 12 のキーはすべて毎回書く（空なら「—」）。キーの抜けは検索・照合の穴になる。
- 参照の書式は `npc:<id>`・`fact:<id>`・`ev:<id>`・`rumor:<id>` の 4 種。id は state.yaml の npcs、
  facts/ のファイル名、world/04_events.md の事件 id、state.yaml の rumors と一致させる。
- 「起きたこと」と「反応」に Canon を書かない。fact に関わる手は `fact:<id>` で参照するだけにする。
- OOC の相談・セーブ・監査は手に数えない（`event_draw.md` §1 と同じ数え方）。

## 3. 検索（Python 版）

```bash
python3 tools/turnlog.py <campaign> --npc berta          # npc:berta が出てくる手
python3 tools/turnlog.py <campaign> --fact toll_pledge   # その事実に関わった手
python3 tools/turnlog.py <campaign> --event ev_widow_petition
python3 tools/turnlog.py <campaign> --from 10 --to 20    # 手番の範囲
python3 tools/turnlog.py <campaign> --text 帳簿          # 文字列検索
```

条件は AND で絞り込む。NPC を再登場させる前に `--npc` で過去の手を読めば、
態度や目撃した出来事と食い違う振る舞いを避けられる。コード無し版では、TURNLOG を貼って
「npc:berta の出てくる手を抜き出して」と頼めば同じことになる（参照書式が固定されているため）。

## 4. ゲートの検査（Python 版。TURNLOG.md があるときのみ）

| # | 検査 | FAIL 条件 |
|---|------|-----------|
| L | 手番連続 | move が 1 から連続していない／最後の move が `meta.move` と一致しない |
| M | 抽選照合 | 抽選した手に対応する `DRAW move=<n>` が CHANGELOG に無い／tier が食い違う。事件のある手に `EVENT move=<n> id=<id>` が無い |
| N | 参照実在 | `npc:`・`fact:`・`ev:` の id が state.yaml・facts/・04_events.md に存在しない |
| O | キー欠落 | 12 のキーのどれかが無い |

P（新設定）・Q（好感照合）・R（噂）は `reaction.md` §6。

## 5. コード無し版

物語の途中に手番ログを挟むと没入が壊れる（GM 契約第4条）。コード無し版では、
GM は毎手の処理を頭の中で済ませ、**セーブ時に前回セーブ以降の TURNLOG をまとめて出力する**。
会話から書き起こすため取りこぼしは起こりうる。人間が最終番人になる点は、他の監査と同じ。
