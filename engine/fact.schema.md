# fact schema — 事実の最小単位

三層を「別ディレクトリ」に割ると同期地獄になる。そうではなく、
**1つの事実(fact)が Canon / Revealed / Belief を属性として持つ。**
これで三層が一望でき、霧・誤り・嘘が同じスキーマの上で区別されて並ぶ。

1事実 = 1ファイル（`facts/<id>.yaml`）。

---

## スキーマ

```yaml
id: <string>              # 一意。ファイル名と一致させる。snake_case推奨
subject: <string>         # この事実が「誰／何」についてか（NPC id・地名・組織名）
tags: [<string>, ...]     # 任意。検索・季節注入のフック用（例: harbor, rival, mil）

canon: <string>           # 真の世界状態。GM専用。playerに直接語ってはならない

revealed:
  status: hidden | partial | full   # 開示度。hidden→partial→full の一方向のみ
  to_player: <string>     # playerに実際に届いている表現。status=hiddenなら空でよい
  channel: <string>       # どのチャネルで開示したか（NPC名・文書・観察）。REVEAL時必須
  at: <string>            # 開示時刻（例: autumn.d14）。REVEAL時必須

belief:
  player_thinks: <string> # playerが真だと思っている内容。未接触なら空
  diverges: <bool>        # player_thinks が canon と食い違っているか
  cause: <string|null>    # 乖離の理由。diverges=true のとき必須。
                          #   例: disinfo(二重間諜) / rumor / player_misread
                          #   null かつ diverges=true は「説明できない乖離」＝ゲートで停止
```

---

## status の意味

| status | player の状態 | 例（役割で記述。固有名は各キャンペーン側） |
|--------|--------------|----|
| `hidden` | この事実の存在すら知らない | 水先案内人が内通者であること自体、誰も疑っていない |
| `partial` | 存在は知るが真相は不明／断片的 | 「水先案内人の素性は怪しい」までは掴んだ |
| `full` | Canonと一致する認識に到達 | 水先案内人が内通者だと確証を得た |

**status は一方向のラチェット。** `full`→`partial` のような後退は、
ほぼ確実にLLMの記憶落ち事故であり、ゲートが停止させる。

---

## diverges と cause の真理値表（ゲートの判定核）

| diverges | cause | 判定 | 意味 |
|----------|-------|------|------|
| false | (無視) | ✅ 正常 | player認識はCanonと整合、または未接触 |
| true | `disinfo(...)` 等あり | ✅ 正常 | **仕様の嘘。** 意図された偽情報 |
| true | null / 空 | ❌ 停止 | **説明できない乖離＝ハルシネーションの温床** |

この一行のためだけに三層がある。`diverges=true & cause=null` を保存前に
炙り出すことが、全知型ハルシネーションへの逆戻りを防ぐ番人になる。

---

## 最小例（未開示の事実）

※ 以下はエンジン説明用の一般例。固有名は使わず役割名詞で書く。

```yaml
id: pilot_loyalty
subject: 水先案内人
tags: [harbor, rival]
canon: "水先案内人は敵対商会に雇われた内通者"
revealed:
  status: hidden
  to_player: ""
  channel: ""
  at: ""
belief:
  player_thinks: ""
  diverges: false
  cause: null
```

## 進行後（偽情報が効いている状態）

```yaml
id: pilot_loyalty
subject: 水先案内人
tags: [harbor, rival]
canon: "水先案内人は敵対商会に雇われた内通者"
revealed:
  status: partial
  to_player: "水先案内人の素性には不審な点がある"
  channel: "尋問(捕虜)"
  at: autumn.d14
belief:
  player_thinks: "水先案内人は中立の技術者で敵とは無関係"
  diverges: true
  cause: "disinfo(二重間諜, autumn.d11)"
```

canon（内通者）と player_thinks（中立）が食い違い、その理由が
`disinfo(...)` として明示されている。ゲートはこれを「仕様の嘘」と認めて通す。
もし cause が空なら、同じ食い違いが「事故」として停止させられる。
