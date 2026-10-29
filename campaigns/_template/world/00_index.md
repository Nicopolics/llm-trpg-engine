# 00 — 世界インデックス

このディレクトリは世界状態(Canon)の人間可読ビュー。GM専用。
各ファイルは「今、真に何がそうであるか」を保持する。playerへの開示は
facts/*.yaml の revealed 層と CHANGELOG が管理する（ここは真実の側）。

| ファイル | 内容 |
|----------|------|
| 01_geography.md   | 地理・拠点・地形 |
| 02_npcs.md        | 人物（正体・動機・関係） |
| 03_factions.md    | 勢力・外部アクター（季節注入の供給源） |
| 04_events.md      | 進行中／過去の事件 |
| 05_economy.md     | 経済・交易・資源 |
| 06_military.md    | 軍事・防備・戦力 |
| 07_institutions.md| 制度・組織・仕組み |
| 08_timeline.md    | 時系列（穴埋めは CHANGELOG に記録） |
| 09_pc.md          | PC（player著作レーン。Canon/factではない） |

## ゼロ状態の始め方
1. 01〜03 を先に埋める（地理・人物・勢力）。世界の骨格。
2. 骨格の中の「伏せたい真実」を facts/ に切り出す（status: hidden）。
3. GM_CONTRACT.md をGMに渡してセッション開始。
