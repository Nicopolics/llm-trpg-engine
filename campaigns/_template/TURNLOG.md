# TURNLOG — 手番ログ

> 仕様: [engine/turnlog.spec.md](../../engine/turnlog.spec.md)
> 雛形（ゼロ状態）。GM の応答 1 回ごとに 1 エントリ追記する（append-only）。
> 12 のキーは毎回すべて書く（空なら「—」）。人物・事実・事件・噂は npc:<id> / fact:<id> / ev:<id> / rumor:<id> で参照する。Canon は書かない。

<!-- 例:
### move 1 | autumn.d01.dawn | 城門前
- 入力: 門を見回す
- 行為: 中立
- 判定: 自動
- 抽選: calm d20=7 tension=0→1
- 事件: —
- 起きたこと: 衛兵 npc:gate_guard が新しい主に気づいて敬礼した。
- 反応: npc:gate_guard 変化なし
- 目撃: npc:gate_guard
- 噂: —
- 新設定: —
- 台帳: —
- 開示: —
-->
