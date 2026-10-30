# llm-trpg-engine

## これは何か

チャットのLLMにGM（ゲームマスター）を担当させてTRPGを遊ぶための、キット（zip）。

世界設定とシナリオは入っていない。持ち込むか、LLMと一緒に作る。
仕組みの概要は「どんな仕組みなのか」に、詳しい構造は後ろの「構造の詳細」にある。遊ぶだけなら、読まなくてよい。

## 何ができるのか

- キャラクター作成なしで、すでに事件が起きている場面から始められる。
- 世界を持ち込むか、舞台と雰囲気の一言から、LLMと一緒に世界を作れる。
- GMは、秘密を、NPCの発言・文書・観察できる出来事を通してしか出さない。あなたのキャラクターの台詞・内心・決定は、あなたが書く。
- 所持金・持ち物・位置・時刻が記録され、金額は価格表から算出される。
- 「セーブ」で保存して、次回、続きから遊べる。
- セーブ前に、記録の食い違いを調べる検査が行われる。
- 季節ごとに、新しい隠し事が0〜2件加わる。

## どうやってやるのか

1. GitHub のリポジトリのページで、緑の「Code」ボタンから「Download ZIP」を選ぶ。
2. 保存した zip を、LLM のチャットに渡す（添付する）。
3. 何かプロンプトを添えて送る。決まった形はない。zip だけを渡す場合も、遊びたい状況を書き添える場合も試している。
   プロンプトがなくても、LLM の側から確認が入り、世界の種の選択肢が示されるなどして、始められている（作者の経験）。
4. セーブしたら、更新されたファイルをダウンロードして保管する。次に遊ぶときは、それを渡す。
   あるLLMで遊んだ続きを、別のLLMで遊ぶこともある。

前提は、ファイルを受け取れる LLM。作者は、複数のLLMで、この方法で始めている。

## どんな仕組みなのか

LLM にGMをさせて長く遊ぶと、序盤の設定を忘れる、開示済みの情報を取り消す、金額や持ち物が食い違う、といった状態の食い違いが起こりうる。
このキットは、規則を指示文だけに置かず、次の3つで担保している。

- GMが従う規則を、契約として文書に定めている。
- 事実と数値を、会話ではなく、ファイルに記録している。
- セーブの前に、記録の食い違いを調べる検査を行う。違反があれば、保存しない。

どのファイルに何を記録し、どの順で処理するかは、後ろの「[構造の詳細](#構造の詳細)」に書いてある。

## 今後どうしていくのか

方針は、長いセッションで状態が食い違わないようにすること。改良の対象は次の2点。

- **検査の拡充。** Python版ゲートは、時刻（`meta.clock`）の巻き戻りを検査していない。クエストとNPCは、id の重複以外を検査していない。
- **コード無し版の精度向上。** 監査をLLMが行うため、見落としがありうる。

現時点で、次の点も未対応。

- `JOURNAL.md` は、どちらの監査でも検査していない。
- `engine/state.schema.md` と `engine/state_ops.md` は、文書内で「レビュー用ドラフト v0.2」と記されている。

## リプレイ例

仕様の書式に沿って作った例で、実際のセッションの記録ではない。LLMの出力は毎回変わる。

**GM**
> 夜明け前、城門の衛兵が叩き起こしに来る——使者が一人、門前で倒れた。意識はない。手には封蝋の押された書状。宛名は"この地の主"とだけある。

**あなた**
> 書状を受け取って、封を切る。

**GM**
> 紙片には一行だけ。「港の水先案内人は信用できる。中立の技術者だ。」署名はない。

**あなた**
> 使者は衛兵に任せる。渡し船で港へ行って、書状にあった水先案内人を探す。

**GM**
> 渡し場で、船頭に銅貨を一枚渡す。船は岸を離れ、朝のうちに港の桟橋に着いた。

**あなた**
> セーブ。

（GMが監査を行い、スナップショットと、台帳・進行メモの更新分を出力する。）

<details>
<summary>GM側で行われていること（記録・検査・セーブの出力）</summary>

**前提**

セッションゼロで、次が記録されている。

- 事実 `pilot_loyalty`: canon は「水先案内人は敵対商会に雇われた内通者」、status は `hidden`
- 台帳: 時刻 `autumn.d01.dawn`、位置「城」、所持金 銅貨8（INIT）、価格表 `ferry_fare` = 銅貨1

**書状の場面**

書状（文書）がチャネルになり、内容は偽情報として扱われる。GMは `CHANGELOG.md` に1行記録する。

```
DISINFO  pilot_loyalty  belief="水先案内人は中立の技術者"  source=二重間諜  at=autumn.d01.dawn
```

**渡し船の場面**

GMは、本文より先に台帳を更新する。

- 参照: `prices.ferry_fare` = 銅貨1、所持金（導出値）= 銅貨8
- 更新:

```
SPEND         player.purse     delta={copper:-1}  reason=ferry_fare  counterparty=船頭  at=autumn.d01.dawn
MOVE          player.position  after=港の桟橋                                           at=autumn.d01.dawn
ADVANCE_TIME  meta.clock       after=autumn.d01.morning
```

**セーブの出力**

```
前回スナップショット: なし（初回）

id | status | channel | at | diverges | cause
pilot_loyalty | hidden | | | true | disinfo(二重間諜, autumn.d01.dawn)

=== 監査結果 ===
A スキーマ    : PASS
B ラチェット  : PASS
C 乖離        : PASS
D チャネル    : PASS
E 消失        : PASS
→ 総合: PASS

=== 台帳監査結果 ===
F 残高導出  : PASS — 銅貨 8 − 1 = 7
G 非負      : PASS
H 在庫実在  : PASS
I save_seq  : PASS
J 価格参照  : PASS — ferry_fare 1 × 1 = 1
K id一意    : PASS
→ 台帳総合: PASS

=== 開示スナップショット (SAVE 1 / autumn.d01.morning) ===
id | status
pilot_loyalty | hidden
=== ここまで ===
```

続けて、更新後の `state.yaml` 全文（省略）、今回の操作の一覧（上の `DISINFO` と `SPEND` `MOVE` `ADVANCE_TIME`）、`[gate passed(manual)] autumn.d01.morning`、次の進行メモが出力される。

```markdown
## 現在地

- 直近の場面: 港の桟橋に着いた。
- 進行中の糸口: 「この地の主」宛ての書状。港の水先案内人は中立の技術者だと述べている。署名はない。
- 私(player)が次にやろうとしていること: 書状にあった水先案内人を探す。

## 経緯

### SAVE 1 / autumn.d01.morning
- 夜明け前、衛兵に起こされた。門前に使者が倒れていた。意識はない。
- 使者が持っていた書状を受け取り、封を切った。「港の水先案内人は信用できる。中立の技術者だ」とある。署名はない。
- 使者を衛兵に任せ、渡し船で港へ向かい、港の桟橋に着いた。
```

次回は、スナップショット、`state.yaml`、進行メモの現在地と直近の経緯を、LLM に渡す。

</details>

## 構造の詳細

中身を詳しく知りたい人向け。遊ぶだけなら、読まなくてよい。

- [入っているもの](#入っているもの)
- [1セッションの流れ](#1セッションの流れ)
- [GMが従う規則](#gmが従う規則)
- [キャンペーンのデータ](#キャンペーンのデータ)
- [開始と進行](#開始と進行)
- [情報の操作](#情報の操作)
- [台帳の操作](#台帳の操作)
- [検査](#検査)
- [設計の背景](#設計の背景)
- [手元のフォルダを直接扱う場合](#手元のフォルダを直接扱う場合)

ルールとデータは markdown と YAML のファイル。Python 版ゲートを使わない範囲では、Python は要らない。

### 入っているもの

```
llm-trpg-engine/
├── README.md / DESIGN.md   ← このファイル / 設計思想
├── START_HERE.md           ← LLMにGMの契約と手順を与える文書（起動プロンプトを含む）
├── VERSION / CHANGELOG.md  ← エンジンのバージョンと変更履歴
├── LICENSE / LICENSES/     ← MIT / CC BY-SA 4.0
├── requirements.txt        ← Python版ゲートの依存（PyYAML）
├── engine/                 ← 全キャンペーン共通。固有名詞・世界設定を含まない
│   ├── GM_CONTRACT.md      ← GMが従う契約（第1〜8条）
│   ├── OPENING_PROTOCOL.md ← 開始の手順（セッションゼロ・一手目）
│   ├── operations.md       ← 開示の操作（REVEAL / DISINFO / CORRECT）
│   ├── season_inject.md    ← 季節注入
│   ├── fact.schema.md      ← 事実（facts/*.yaml）のスキーマ
│   ├── state.schema.md     ← 台帳（state.yaml）のスキーマ
│   ├── state_ops.md        ← 台帳の操作（SPEND / MOVE など）
│   ├── journal.spec.md     ← 進行メモ（JOURNAL.md）の仕様
│   ├── changelog.spec.md   ← CHANGELOG.md の書式
│   └── AUDIT_PROTOCOL.md   ← コード無しの監査手順
├── tools/
│   └── export_gate.py      ← Python版ゲート
└── campaigns/
    ├── _template/          ← 空のキャンペーン雛形
    │   ├── world/          ← 00 目次、01 地理、02 人物、03 勢力、04 事件、05 経済、06 軍事、07 制度、08 時系列、09 PC
    │   ├── facts/          ← _TEMPLATE.yaml（書式）、example_harbor_pilot.yaml（見本）
    │   ├── state.yaml      ← 台帳
    │   ├── saves/          ← スナップショットの置き場
    │   ├── CHANGELOG.md    ← 操作ログ
    │   ├── JOURNAL.md      ← 進行メモ
    │   └── README.md
    └── <yours>/            ← あなたのキャンペーン（雛形のコピー）
```

世界設定とシナリオは入っていない。雛形には、書き方の見本として事実が1件（`example_harbor_pilot.yaml`）だけ入っている。
世界は `campaigns/<name>/` の中に閉じる。`engine/` と `tools/` は、複数のキャンペーンで共通に使う。

### 1セッションの流れ

| 段階 | GMがすること | 読み書きするファイル |
|------|-------------|--------------------|
| 開始（セッションゼロ） | 世界の骨格と、プレイヤーに伏せた事実を最低1つ作る。初期状態の台帳を書く。最初の発話は、すでに動いているイベントの途中から始める | 書く: `world/*.md`、`facts/*.yaml`、`state.yaml` |
| プレイ中（情報） | 3つの操作で情報を出し、`CHANGELOG.md` に1行記録し、対応する事実の `revealed` / `belief` を更新する | 読み書き: `facts/*.yaml`、`CHANGELOG.md` |
| プレイ中（状態） | 参照→差分→更新→本文の順で処理し、`CHANGELOG.md` に1行記録する | 読み書き: `state.yaml`、`CHANGELOG.md` |
| セーブ | 監査を行う。合格なら、スナップショットを出し、`JOURNAL.md` の現在地を更新して経緯に追記する。FAIL なら、保存しない | 読む: `facts/*.yaml`、`state.yaml`、前回のスナップショット。書く: `saves/`（Python版）、`JOURNAL.md`、`CHANGELOG.md`（ゲート通過の印） |
| 次回 | 保管したファイルを受け取り、`JOURNAL.md` の現在地から再開する | 読む: 前回のスナップショット、`state.yaml`、`JOURNAL.md`（現在地と直近の経緯） |

### GMが従う規則

| 規則 | 出典 |
|------|------|
| Canon（世界の真の状態）を、地の文で直接語らない。NPCの発言・文書・観察できる出来事を通して伝える | `engine/GM_CONTRACT.md` 第1条 |
| Canon / Revealed / Belief を区別する。プレイヤーがまだ聞いていないことを、NPCが知っている前提で話さない | 第2条 |
| プレイヤーキャラクターの台詞・内心・決定はプレイヤーが書く。GMは選択肢を示してよいが、代行しない | 第3条 |
| 世界状態の確認や整合性の検査は、物語の外で行い、ナレーションに混ぜない | 第4条 |
| `REVEAL` / `DISINFO` / `CORRECT` を、`CHANGELOG.md` に1行記録する | 第5条 |
| セーブ前に監査を行い、1件でも FAIL なら保存しない | 第6条、`engine/AUDIT_PROTOCOL.md` |
| 所持金・持ち物・位置・時刻・進行は `state.yaml` を唯一の正とする。金額は価格表から算出する | 第7条 |
| セーブ時に `JOURNAL.md` の現在地を更新し、経緯に追記する。書くのはプレイヤーに表出したことだけ | 第8条 |
| キャラクター作成を求めない。すでに動いているイベントの途中から始める | `engine/OPENING_PROTOCOL.md` 条件3・4 |

### キャンペーンのデータ

キャンペーンごとに、次のファイルを持つ。

| ファイル | 内容 | 更新するもの |
|----------|------|-------------|
| `world/*.md` | 世界の状態（Canon）。GM専用の人間可読ビュー。`09_pc.md` だけは、プレイヤーの覚え書きで、Canon でも事実でもない | GM（09 はプレイヤー） |
| `facts/*.yaml` | 事実1件につき1ファイル。`canon` / `revealed` / `belief` を持つ | GM |
| `state.yaml` | 所持金・持ち物・位置・時刻・クエスト進行。所持金は収支履歴から残高を導出する | GM |
| `saves/` | セーブ時のスナップショット | ゲート（Python版） |
| `CHANGELOG.md` | 開示操作・状態操作・ゲート通過の追記ログ | GM、ゲート |
| `JOURNAL.md` | 現在地（上書き）と経緯（追記） | GM |

#### 事実（`facts/*.yaml`）

| フィールド | 内容 |
|-----------|------|
| `id` | 一意。ファイル名と一致させる |
| `subject` | 誰／何についての事実か |
| `tags` | 任意。検索・季節注入のフック |
| `canon` | 真の世界状態。GM専用。プレイヤーに直接語らない |
| `revealed.status` | 開示度。`hidden` / `partial` / `full`。一方向のみ |
| `revealed.to_player` | プレイヤーに実際に届いた表現 |
| `revealed.channel` / `revealed.at` | 開示したチャネルと時刻。status が `hidden` より上なら必須 |
| `belief.player_thinks` | プレイヤーが真だと思っている内容 |
| `belief.diverges` | `canon` と食い違っているか |
| `belief.cause` | 食い違いの理由。`diverges: true` なら必須 |

| status | プレイヤーの状態 |
|--------|----------------|
| `hidden` | この事実の存在すら知らない |
| `partial` | 存在は知るが、真相は不明、または断片的 |
| `full` | Canon と一致する認識に到達している |

| `diverges` | `cause` | 判定 |
|-----------|---------|------|
| false | 無視 | 正常 |
| true | `disinfo(...)` など | 正常。意図された偽情報 |
| true | 空 | 停止。説明できない食い違い（検査 C） |

事実ファイルの例（`campaigns/_template/facts/example_harbor_pilot.yaml` を要約）:

```yaml
id: example_harbor_pilot
subject: 水先案内人
canon: "水先案内人は敵対商会に雇われた内通者。港の防備情報を流している"

revealed:                      # プレイヤーに明かした分
  status: partial              # hidden → partial → full
  to_player: "水先案内人の素性には不審な点がある、との証言を得た"
  channel: "捕虜の尋問"
  at: sample.d14

belief:                        # プレイヤーが信じていること
  player_thinks: "水先案内人は中立の技術者で、敵とは無関係"
  diverges: true               # 真実とずれている
  cause: "disinfo(二重間諜, sample.d11)"   # ずれの理由（誰の嘘か）
```

#### 台帳（`state.yaml`）

| 項目 | 内容 |
|------|------|
| `meta` | `campaign`、`save_seq`（セーブの通し番号）、`clock`（現在時刻） |
| `prices` | 参照用の価格表。`id` / `label` / `amount` / `unit` |
| `player.position` / `player.hp` | 現在値。上書きで更新する |
| `player.purse` | `history`（収支履歴。追記のみ）と `balances`（導出値。履歴の総和） |
| `player.inventory` | 所持品。`id` / `label` / `qty` |
| `quests` | 進行。`id` / `stage` / `status` |
| 任意 | `equipment`、`abilities`、`npcs`、`weather`。そのキャンペーンで効くときだけ足す |

物質的なPCの状態（所持金・持ち物・HP・位置）は台帳に置く。PCの人格（性格・生い立ち・動機）は、プレイヤーのもので、台帳にも事実にも置かない。

#### 進行メモ（`JOURNAL.md`）

仕様は [engine/journal.spec.md](engine/journal.spec.md)。

- 構成は、「現在地」（上書き）と「経緯」（追記のみ）。経緯の見出しは `### SAVE <通し番号> / <ゲーム内時刻>`。
- 書くのは、プレイヤーに表出したことだけ。伏せた真実は書かない。
- 台帳と事実の値は書き写さない。JOURNAL から状態を復元しない。
- 再開時に渡すのは、現在地と直近の経緯（目安は3セーブ分）。

### 開始と進行

- 開始時に、GMが世界の骨格と、プレイヤーに伏せた事実（`status: hidden`）を最低1つ作り、初期状態の台帳を書く（`OPENING_PROTOCOL.md` 条件1）。
- 最初のGM発話は、状況を出し、人物を決めず、チャネルを伴い、伏せた事実を解決しない形にする（条件4）。例:

  > 夜明け前、城門の衛兵が叩き起こしに来る——使者が一人、門前で倒れた。
  > 意識はない。手には封蝋の押された書状。宛名は"この地の主"とだけある。

- 季節ごとに、外部アクターが新しい伏せた事実を0〜2件加える。0件の季節もある（[engine/season_inject.md](engine/season_inject.md)）。

### 情報の操作

情報の出し方は、次の3つの操作に限られる。GMは、操作のたびに `CHANGELOG.md` へ1行記録する（`engine/operations.md`）。

| 操作 | 内容 |
|------|------|
| `REVEAL` | 真実の一部をプレイヤーに明かす。`hidden → partial → full` の一方向のみで、後退しない。チャネルを必ず伴う |
| `DISINFO` | NPCが意図的に嘘をつく。プレイヤーの認識を真実からずらす。誰の嘘かを必ず記録する |
| `CORRECT` | 嘘や誤解が解け、認識が真実に戻る |

ひとつの事実の記録例:

```
DISINFO  pilot_loyalty  belief="水先案内人は中立の技術者"  source=二重間諜     at=autumn.d11
REVEAL   pilot_loyalty  partial  via=尋問(捕虜)                           at=autumn.d14
CORRECT  pilot_loyalty  via=証拠露見(積荷台帳)                            at=autumn.d16
REVEAL   pilot_loyalty  full     via=証拠露見(積荷台帳)                   at=autumn.d16
```

地の文で真相を述べるのは第1条に反する例:

- ❌ 「水先案内人は実は敵の内通者だ」
- ✅ 捕虜が吐いた——「水先案内人？ ああ、あいつは"向こう側"の人間だよ」

### 台帳の操作

状態が動くターンでは、GMは次の順で処理する（`engine/state_ops.md`）。

1. 参照: 現在の `state.yaml` と価格表を読む。
2. 差分: 変化量を、参照した値から計算する。
3. 更新: `state.yaml` を1箇所書き換える（所持金は履歴に1行追記、位置・時刻などは1フィールド上書き）。
4. 本文: 更新後の状態に基づいて書く。

差分を台帳と価格表から確定できないときは、本文を書かずに止まり、不足を物語の外で伝える。
操作の種類は、`SPEND` / `GAIN` / `ACQUIRE` / `CONSUME` / `DROP` / `MOVE` / `ADVANCE_TIME` / `SET_QUEST` など。

### 検査

セーブ前に、次の検査を行う。1件でも FAIL なら、保存しない。

| 対象 | 検査 |
|------|------|
| 開示（`facts/`） | A スキーマ / B ラチェット（status が前回より後退していないか）/ C 乖離の正当性（`diverges: true` なのに `cause` が空でないか）/ D チャネル整合 / E 消失（前回 partial・full の事実が消えていないか） |
| 台帳（`state.yaml`） | F 残高導出（残高 = 収支履歴の総和）/ G 非負 / H 在庫実在 / I `save_seq` の後退 / J 価格参照（金額 = 価格 × 個数）/ K id の重複 |

実行方法は2つある。

| | コード無し版 | Python版 |
|---|---|---|
| 実行するもの | LLM（手順: `engine/AUDIT_PROTOCOL.md`） | `tools/export_gate.py` |
| 確認 | 人間が表を目視する | スクリプトが判定する |
| 制限 | LLMが検査するため、見落としがありうる | Python と PyYAML が必要 |

未確認: Python 版ゲートを、各LLMのサービスで実行できるか。

### 設計の背景

上の「どんな仕組みなのか」で述べた状態の食い違いを、このリポジトリでは「ドリフト」と呼ぶ。
規則を指示文だけに置かず、次の3つで担保する。

- 事実を `facts/*.yaml` に分けて持つ。
- 数値を `state.yaml` に持つ。所持金は収支履歴から導出し、金額は価格表を参照して決める。
  （例: 渡し船の運賃が、行きは1銅貨、帰りは6銅貨になる食い違い）
- セーブ前に検査し、違反があれば保存しない。

事実は、次の三層で持つ。

| 層 | 誰のものか | 内容 | 検査での扱い |
|----|-----------|------|-------------|
| **Canon** | GM / 世界 | 世界の真の状態 | これに反するGM発話は誤り |
| **Revealed** | プレイヤーの知識 | Canonのうち明かした分。追記のみ | 縮んでいたら開示の消失（検査 B・E） |
| **Belief** | プレイヤーの認識 | Canonとずれうる | ずれに `cause` があれば偽情報、なければ誤り（検査 C） |

設計思想の詳細は [DESIGN.md](DESIGN.md) を参照。

### 手元のフォルダを直接扱う場合

LLM を介さずに、または LLM とは別に、自分でフォルダを操作する場合の手順。

#### 自分の世界を作る

雛形をコピーして、埋める。

```bash
cp -r campaigns/_template campaigns/myworld
```

- `world/*.md` — 世界の状態。まず 01〜03（地理・人物・勢力）を埋める。
- `facts/*.yaml` — プレイヤーに伏せたい事実を、1事実につき1ファイルで書く。
- `state.yaml` — 所持金・持ち物・位置・時刻などの台帳。

#### Python版ゲートを使う

必要なもの: Python 3.9+ と PyYAML（`pip install pyyaml`）。

```bash
python3 tools/export_gate.py myworld            # 監査して、合格なら saves を更新し CHANGELOG.md に追記
python3 tools/export_gate.py myworld --dry-run  # 監査のみ。書き込まない
```

`campaigns/` に実キャンペーンが1つだけなら、名前は省略できる。

## バージョン

[Semantic Versioning](https://semver.org/lang/ja/) に従う。現行バージョンは [VERSION](VERSION)、
変更履歴は [CHANGELOG.md](CHANGELOG.md)（エンジン本体のリリースノート。キャンペーンごとの `CHANGELOG.md` とは別）。
既存キャンペーンの `facts/` や `state.yaml` がそのままでは使えなくなる変更は MAJOR を上げ、移行手順を添える。

## ライセンス

- `tools/`（Python版ゲート）— MIT。全文は [LICENSE](LICENSE)
- ドキュメント・スキーマ（`engine/`・`campaigns/_template/` と各 `.md` / `.yaml`）— CC BY-SA 4.0。全文は [LICENSES/CC-BY-SA-4.0.txt](LICENSES/CC-BY-SA-4.0.txt)

Copyright (c) 2026 Nicopolics

個人プロジェクト。Issue/PR は歓迎するが、応答は約束しない。
