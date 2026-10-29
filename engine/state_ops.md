# state 操作 — 物質状態の型付きミューテーション

**［レビュー用ドラフト v0.2］** `operations.md`（開示操作）の物質版。
状態変化は自由記述ではなく型のある動詞に限定し、changelog とゲートが検算できる形にする。

> v0.2：**1 変更＝1 書き込み**に統一（→ `state.schema.md §1`）。
> 累積値（金）は履歴 1 行の追記だけ、点値（位置・HP・時刻・段階）は
> 1 フィールドの上書きだけ。同じ事実を 2 箇所に書かせない。

---

## 0. 中核原則 — 参照→差分→更新→本文

状態が動くターンでは、GM は **必ずこの順**で処理する。順序を入れ替えない。

```
1. 参照   現在の state.yaml を読む（記憶ではなく、書かれた値を読む）
2. 差分   変化量を計算する。金額・距離・時間は必ず該当の値を「参照」して算出
3. 更新   state.yaml を 1 箇所書き換える（履歴 1 行 追記 / 点値 1 フィールド 上書き）
4. 本文   更新後の State に基づいて物語を書く
```

これに反する2つを禁止する：

- ❌ 「後で更新する」——本文を先に書いて台帳を後回しにする
- ❌ 「会話履歴から復元する」——State ではなく本文・記憶から数値を再構成する

### fail-closed（更新できなければ止まる）

差分を State と価格表から**確定できない**とき（値が無い／矛盾する）、
GM は **本文を書かず停止**し、OOC で不足を宣言する。推測で数値を埋めない。
不明時の許容手は3つだけ：**確認する / 不明として据え置く / GM視点でも不明とする。**

### 推測禁止リスト

State が存在する限り、次を記憶・一般知識から推測しない：
所持金・所持品・HP・時刻・距離・日数・評判(disposition)・NPC状態・クエスト進行・**価格**。

### 参照の優先順位（数値の出どころ）

```
1. state.yaml（唯一の正）        4. セッション本文
2. prices（価格表）              5. 世界設定 world/*.md
3. システムルール                6. AI一般知識（最後の手段。State がある限り使わない）
```

---

## 1. 書式と「書く場所は1つ」

changelog へ 1 行ログする。書式：

```
<OP>  <target>  <delta or after>  reason=<...>  at=<time>
```

state.yaml への反映は種類で 1 箇所に限る：

- **累積値（purse）** … `history` に 1 行 **追記**する（`delta` が本体）。
  `balances` は書き換えない——ゲートが履歴から再計算する導出値だから。
  ※ ログ行に前後残高を併記してよいが、それは可読性のための導出情報。
- **点値（position/hp/clock/quest/inventory の qty 等）** … 該当フィールドを
  **1 つ上書き**する。履歴は state.yaml 内に二重に持たない（監査証跡は changelog）。

---

## 2. 動詞一覧

| OP | 対象 | 効果 | state.yaml への書き込み |
|----|------|------|--------------------------|
| `INIT` | purse/inventory 等 | 初期状態の確立（セッションゼロのみ） | 履歴追記 or 点値設定 |
| `SPEND` | purse | 支払い。額は `prices[reason]` を参照 | history に 1 行追記（delta 負） |
| `GAIN` | purse | 収入 | history に 1 行追記（delta 正） |
| `ACQUIRE` | inventory | 入手（qty 増／新規） | inventory を 1 項目更新 |
| `CONSUME` | inventory | 消費（qty 減）。不所持は不可 | inventory を 1 項目更新 |
| `DROP` | inventory | 手放す。不所持は不可 | inventory を 1 項目更新 |
| `EQUIP`/`UNEQUIP` | equipment（任意） | 着脱 | equipment を 1 項目更新 |
| `MOVE` | player.position | 移動 from→to | position を上書き |
| `ADVANCE_TIME` | meta.clock | 時刻を進める（単調増加のみ） | clock を上書き |
| `DAMAGE`/`HEAL`/`SET_HP` | player.hp | HP 変動 | hp を上書き |
| `SET_QUEST` | quests | 段階・状態の遷移 | 該当 quest を上書き |
| `SET_NPC` | npcs（任意） | disposition/alive/location | 該当 npc を上書き |
| `SET` | 上記外 | 汎用（abilities 等の機械的値） | 該当フィールド上書き |

---

## 3. 価格は必ず参照する（1銅貨→6銅貨 事故の直接対策）

支払いの額を**記憶や一般知識から作らない**。必ず `prices` の id を引く。

- ❌ 記憶で `2 copper` と決めて払う
- ✅ 手順：
  1. `prices.ferry_fare` を**参照** → `amount:1, unit:copper`
  2. `player.purse` の現残高（導出値）を参照 → `copper:8`
  3. `history` に 1 行追記（これだけが書き込み）：
  ```
  SPEND  player.purse  delta={copper:-1}  reason=ferry_fare  counterparty=船頭  at=autumn.d01.dawn
  ```
  balances は書かない。ゲートが `Σ history = copper:7` を再計算する。

帰り便も同じ `ferry_fare` を参照するので **1 銅貨に固定**。運賃を変えるときは、
先に `prices.ferry_fare.amount` を更新してから `SPEND` する（値の出どころは常に価格表）。

複数個買うときは `qty` を添える（既定 1）。ゲートは `|delta| == amount × qty` を
検算する：

```
SPEND  player.purse  delta={copper:-4}  qty=4  reason=bread  counterparty=パン屋  at=...
```

`bread=2` × `qty=4` = 8 ではなく 4 を払っていれば検査 J で停止する。逆に「1 個の
運賃を 6 で処理」も `amount(1)×qty(1)=1 ≠ 6` で弾かれる。

---

## 4. ライフサイクル例（渡し船で往復し、パンを買う）

changelog ログ（各行が state.yaml の 1 箇所を動かす）：

```
SPEND         player.purse     delta={copper:-1}  reason=ferry_fare  counterparty=船頭   at=autumn.d01.dawn
MOVE          player.position  after=対岸の村                                            at=autumn.d01.dawn
ADVANCE_TIME  meta.clock       after=autumn.d01.morning
SPEND         player.purse     delta={copper:-2}  reason=bread       counterparty=パン屋  at=autumn.d01.morning
ACQUIRE       player.inventory after={id:bread,label:黒パン,qty:1}   reason=購入(bread)   at=autumn.d01.morning
SPEND         player.purse     delta={copper:-1}  reason=ferry_fare  counterparty=船頭   at=autumn.d01.noon
MOVE          player.position  after=港の桟橋                                            at=autumn.d01.noon
```

導出後の残高 `copper:4`（= 8 −1 −2 −1）はゲートが履歴から再計算（検査 F 合格）。
往復とも運賃は `ferry_fare=1` で処理され、事故は構造的に起きない。
**この 7 行で人が書いたのは、各行 1 箇所ずつだけ。**

---

## 5. 禁止事項

- 本文を先に書いて台帳を後で直す（原則0違反）
- 会話履歴・記憶から残高やアイテムを復元する（同上）
- 価格表を経由しない金額の算出（検査 J で停止）
- `history` を追記せず `balances` を直接いじる（検査 F で停止。balances は導出値）
- 同じ変化を history と点値の両方に二重記録する（更新点を増やすな）
- 所持していない物の `CONSUME`/`DROP`（検査 H で停止）
- `meta.clock` を後退させる（検査 I で停止）
- 差分を確定できないのに本文へ進む（fail-closed 違反。停止して確認せよ）
