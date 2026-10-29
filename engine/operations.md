# 開示操作 — REVEAL / DISINFO / CORRECT

開示は自由記述ではなく、型のある3つの動詞に限定する。
これで changelog が自動で意味を持ち、ゲートが事故と仕様を区別できる。

セッション中、GMがplayerに情報を届ける／偽情報を流す／嘘が露見するたびに、
対応する操作を1行ログとして記録する（`CHANGELOG.md`）。
このログが、fact yaml の `revealed` / `belief` を更新する根拠になる。

---

## 書式

```
<OP>  <fact_id>  <args...>  at=<time>
```

## 3つの動詞

### REVEAL — Canon を Revealed にコミットする（不可逆）

```
REVEAL  <fact_id>  <new_status>  via=<channel>  at=<time>
```

- `revealed.status` を上げる（hidden→partial→full の一方向のみ）
- `revealed.to_player` と `revealed.channel` を更新
- **必ず channel を伴う。** チャネルなき REVEAL は GM契約違反（監査モード）
- 例：
  ```
  REVEAL  pilot_loyalty  partial  via=尋問(捕虜)  at=autumn.d14
  ```

### DISINFO — Belief を Canon から意図的に乖離させる

```
DISINFO  <fact_id>  belief="<player_thinks>"  source=<who>  at=<time>
```

- `belief.player_thinks` を設定、`belief.diverges=true`、
  `belief.cause="disinfo(<source>)"` を書き込む
- これが「NPCが嘘をつく」の実体。**嘘を操作として明示する**ことで、
  ゲートが後で「仕様の嘘」と判定できるようになる
- 例：
  ```
  DISINFO  pilot_loyalty  belief="水先案内人は中立の技術者"  source=二重間諜  at=autumn.d11
  ```

### CORRECT — Belief を Canon へ再収束させる（嘘の露見・誤解の解消）

```
CORRECT  <fact_id>  via=<channel>  at=<time>
```

- `belief.diverges=false`、`belief.cause=null` に戻す
- 多くの場合、同時に `REVEAL ... full` を伴う（真相が判明したため）
- 例：
  ```
  CORRECT  pilot_loyalty  via=証拠露見(積荷台帳)  at=autumn.d16
  REVEAL   pilot_loyalty  full  via=証拠露見(積荷台帳)  at=autumn.d16
  ```

---

## ライフサイクル例（1つの事実の一生）

```
# 事実誕生（hidden、ログ不要。fact yaml を新規作成した時点）

DISINFO  pilot_loyalty  belief="水先案内人は中立の技術者"  source=二重間諜       at=autumn.d11
REVEAL   pilot_loyalty  partial  via=尋問(捕虜)                       at=autumn.d14
CORRECT  pilot_loyalty  via=証拠露見(積荷台帳)                        at=autumn.d16
REVEAL   pilot_loyalty  full     via=証拠露見(積荷台帳)               at=autumn.d16
```

hidden（誰も知らない）→ 偽情報で誤認させ → 尋問で断片が漏れ →
物証で嘘が割れ → 真相確定。**この4行が、playerの知識のバージョン履歴**であり、
物語のプロットそのものでもある。

---

## 禁止事項

- `REVEAL` で status を**下げない**（ラチェット違反、ゲートが停止）
- `channel` なしの `REVEAL` を書かない（GMがCanonを地の文で漏らした証拠）
- `DISINFO` の `source` を空にしない（誰の嘘か不明＝事故と区別不能）
