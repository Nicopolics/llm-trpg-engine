# CHANGELOG 仕様

`CHANGELOG.md` は3つの役割を兼ねる。

1. **開示ログ** — セッション中の `REVEAL` / `DISINFO` / `CORRECT` の記録（GMが追記）
2. **状態ログ** — `SPEND` / `GAIN` / `MOVE` / `ADVANCE_TIME` 等、物質状態の変更の記録
   （GMが追記 → `engine/state_ops.md`）。台帳の点値更新の監査証跡を兼ねる
3. **ゲートログ** — `export_gate.py` が保存を通すたびに追記する監査済み印

append-only。過去のエントリを書き換えない。

ここに書くのは型付き操作だけ。物語の経緯と現在地は `JOURNAL.md` に書く（→ `journal.spec.md`）。

---

## 書式

```
## <session-id / date>  (<time-in-world>)

### 開示操作
REVEAL   <fact_id>  <status>  via=<channel>  at=<time>
DISINFO  <fact_id>  belief="..."  source=<who>  at=<time>
CORRECT  <fact_id>  via=<channel>  at=<time>

### 状態操作（台帳を使うとき）
SPEND    player.purse  delta={copper:-1}  reason=<price_id>  counterparty=<who>  at=<time>
MOVE     player.position  after=<場所>  at=<time>
ADVANCE_TIME  meta.clock  after=<time>

### 世界ギャップ埋め（あれば）
- <fact_id or file>: <何を、なぜ補填したか>

### ゲート
[gate passed] <ISO timestamp>  facts=<n>  revealed_delta=+<k>
```

---

## world-gap の明記

セッション間でデータの穴（移行ギャップ・後から思い出した設定）を埋めたときは、
**必ずここに記録する。** 何を、なぜ足したかを一行残す。原ノートがあるなら
ポインタも。これがないと、後から「この設定はいつ生えた？」を追えなくなる。

例：
```
### 世界ギャップ埋め
- timeline autumn.d02-d22: セッション移行時に欠落。原ノート notes/autumn_raw.md から復元
```

「procedures are forgotten, mechanisms are not」——だから穴埋めも
手順（覚えておく）ではなく機構（ログに残す）で扱う。

---

## ゲートによる自動追記

`export_gate.py` は合格時に `[gate passed]` 行を末尾に足す。
この行があることが「この保存は三層の整合を通過した」の証明になる。
ゲートを通さない保存には、この印がつかない。
