# state schema — 物質状態の唯一の正（single source of truth）

**［レビュー用ドラフト v0.2］** 新機構「物質状態台帳」の設計案。
確定後に GM契約・ゲート・開始プロトコルへ展開する。

> v0.2 の変更：**同時更新箇所を増やさない**を最優先の設計制約に据えた。
> 冗長な二重保持を排し、「1 変更＝1 書き込み」に縮約した（§1）。

---

## 0. なぜ facts/ とは別レーンなのか

`facts/*.yaml`（三層開示エンジン）が守るのは「**誰が何を知っているか**」という
**認識の一軸**だけである。所持金・価格・在庫・HP・時刻・位置・クエスト進行と
いった「**量的・機械的な事実**」はそこに乗らない。ここが従来キットの穴で、
数値を State から読まず一般知識から補完した瞬間に破綻する
（例：行き 1 銅貨の運賃が、帰りに記憶から 6 銅貨で処理される事故）。

対策は開示軸と同じ思想の適用——**正しさを指示から機構へ**。物質状態を
`state.yaml`（唯一の正）に置き、変更を型付き操作で行い、保存前にゲートで検算する。

### facts/ との棲み分け（フィールドは重複させない）

| | facts/（開示層） | state.yaml（物質層） |
|---|---|---|
| 扱う対象 | 隠し事実・嘘・開示度 | 数値・在庫・位置・時刻・進行 |
| 層構造 | Canon/Revealed/Belief の三層 | **無し。フラットな現在値1枚** |
| 目的 | 情報非対称・没入 | 整合・検算 |

**同じ事実を両方に書かない。** 「価格が本当は吊り上げられている」等の
開示演出が要る隠し事実は facts/ 側で `DISINFO` として扱い、state.yaml は
常に“真の数値”だけを持つ。この排他性が二重管理を防ぐ。

**この台帳に公開/非公開の区別は設けない。** GM の計算台帳であり、player が
値を覗いてもそれは player 側の自己責任。GM 側で分離管理はしない。

---

## 1. 設計制約 — 更新点を増やさない（最重要）

台帳導入の最大のリスクは「同期すべき場所が増える」こと。これを機構で抑える。

1. **1 ファイル。** 物質状態はすべて単一の `campaigns/<name>/state.yaml` に置く。
   ドメイン別ファイルに割らない（割ると同期地獄になる。facts/ の教訓と同じ）。
2. **累積値は履歴だけを書く。残高は導出。**
   所持金は `history` への 1 行追記だけがオーサリング対象。`balances` は
   `Σ(history.delta)` の**導出値（キャッシュ）**であり、手で history と同期しない。
   ゲートが history から再計算し、書かれた `balances` と照合する（drift 検出）。
   → **「残高＋履歴」要件は満たすが、書く場所は履歴 1 箇所だけ。**
3. **点値は現在値だけを持つ。** 位置・HP・時刻・クエスト段階などは “いまの値”
   1 フィールドを上書きする。state.yaml 内に履歴を二重に持たせない
   （変更の監査証跡は `CHANGELOG.md` の操作ログが兼ねる → `state_ops.md`）。
4. **参照データは読み取り専用寄り。** `prices` は変更時のみ更新する静的表で、
   毎ターン触る対象ではない。
5. **スナップショットは写し。** セーブ時に `state.yaml` を `saves/` へコピーする
   だけ。並行して育てる別ソースにしない。

要するに、**1 回の状態変化で人が書くのは原則 1 箇所**（履歴なら 1 行追記、
点値なら 1 フィールド上書き）。これが煩雑さを増やさないための背骨。

---

## 2. 置き場所

- ライブ状態：`campaigns/<name>/state.yaml`（現在の唯一の正。常にここを読む）
- スナップショット：セーブ時に `saves/` へ写しを取る（開示スナップショットと同梱）

コード無し版では、`state.yaml` 全文を人間が持ち回り、次回冒頭に貼る。
これで台帳の土台も LLM の記憶の外に出る。

---

## 3. スキーマ（コア＝必須 / オプション＝必要時のみ）

**煩雑さを避けるため、既定で追うのはコアだけ。** 装備・能力値・NPC・天候は
そのキャンペーンで実際に効くときだけ足す（使わない欄は作らない）。

```yaml
meta:
  campaign: <string>
  save_seq: <int>
  clock: <string>           # 現在時刻。例 autumn.d14.morning。単調増加（点値）
  # weather: <string>       # 【オプション】天候を機械的に扱う必要があるときだけ

prices:                     # 参照データ。使う項目だけ載せる。変更時のみ更新
  - { id: <string>, label: <string>, amount: <number>, unit: <string> }

player:
  position: <string>        # 現在地（点値）。移動は MOVE
  hp: { current: <int>, max: <int> }   # （点値）
  purse:
    history:                # ★オーサリングはここだけ（append-only）
      - { at: <time>, op: <OP>, delta: { <unit>: <±int> },
          reason: <string>, counterparty: <string|null>, qty: <int> }
          # qty は任意（既定 1）。reason が prices の id を指すとき、ゲートは
          #   |delta[unit]| == price.amount × qty を検算する（検査 J）。
          #   「運賃1銅貨を6で処理」のような記憶補完を機械的に弾く要。
    balances: { <unit>: <int> }        # 導出値。Σ(history.delta)。ゲートが再計算・照合
  inventory:                # 所持品（消耗品含む）。現在の在庫（点値の集合）
    - { id: <string>, label: <string>, qty: <int> }
  # equipment: [...]        # 【オプション】{ slot, id, label }
  # abilities: [...]        # 【オプション】{ id, value } 機械的な値のみ

quests:                     # 進行（段階・状態は点値）
  - { id: <string>, stage: <int>, status: active|done|failed }

# npcs: [...]               # 【オプション】{ id, disposition, alive, location }
```

---

## 4. 不変条件（ゲートが検算する）

保存前に機械チェック。1 件でも破れたら **FAIL＝保存拒否・進行停止**。

| # | 検査 | FAIL条件 |
|---|------|----------|
| F | 残高導出 | `balances[unit]` が `Σ(history.delta[unit])` と不一致（手書き drift） |
| G | 非負     | `balances` に暗黙の負値（借金を許すなら `debt` を明示） |
| H | 在庫実在 | 「所持していない物」を CONSUME/DROP している |
| I | 時刻単調 | `meta.clock` が前回スナップショットより後退 |
| J | 価格参照 | `reason` が `prices` の id を指すのに `\|delta\|≠amount×qty`（記憶補完） |
| K | id一意   | `prices`/`inventory`/`quests`（＋使うなら npcs）の id 重複 |

F と J が「1銅貨→6銅貨」事故の直接の番人：残高は履歴の総和でしか動かず、
取引額は価格表の参照でしか作れない。**記憶から数値を生む経路を構造的に塞ぐ。**

---

## 5. PC の「物質状態」と「人格」を分ける

player 主権（PC の内面・過去・決定は player の所有物、Canon にも fact にも
載せない）は維持する。切り分けを一段細かくする。

- **物質的 PC 状態**（財布・在庫・HP・位置・能力値）＝客観的・機械的。
  → state.yaml で台帳管理。これは主権の対象ではない（GM が計算する数値）。
- **物語的 PC 人格**（性格・生い立ち・動機）＝主観的・主権的。
  → 従来どおり player の手元（`world/09_pc.md`）。台帳にも facts/ にも載せない。

「あなたは 3 銅貨しか持っていない」は台帳が言える。
「あなたは復讐に燃えている」は台帳が言ってはいけない。

---

## 6. 完全な例（初期状態を書き込んだセーブ＝空台帳ではない）

```yaml
meta:
  campaign: harbor
  save_seq: 0
  clock: autumn.d01.dawn

prices:
  - { id: ferry_fare, label: "渡し船 片道", amount: 1, unit: copper }
  - { id: bread,      label: "黒パン",     amount: 2, unit: copper }

player:
  position: 港の桟橋
  hp: { current: 10, max: 10 }
  purse:
    history:
      - { at: autumn.d01.dawn, op: INIT, delta: { copper: 8 },
          reason: "初期所持金", counterparty: null }
    balances: { copper: 8 }        # = Σ history（+8）。ゲートが再計算して照合
  inventory:
    - { id: rope, label: "麻縄", qty: 1 }

quests: []
```

`balances.copper: 8` は `history` の総和（+8）から導出（検査 F 合格）。
運賃を払う操作は `state_ops.md` の `SPEND ... reason=ferry_fare` で、額は必ず
`prices.ferry_fare`＝1 を参照する。帰り便も同じ参照を通るので 6 にはなり得ない。
