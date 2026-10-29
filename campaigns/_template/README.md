# キャンペーン: _template

これは空のキャンペーン雛形。**新しいキャンペーンはこれを丸ごとコピーして始める。**

```bash
cp -r campaigns/_template campaigns/<your_campaign>
python3 tools/export_gate.py <your_campaign>
```

このフォルダの中身（world/ facts/ state.yaml saves/ CHANGELOG.md JOURNAL.md）は
**このキャンペーン専用**。engine/ と tools/ は全キャンペーンで共有される。
エンジンを触らずに世界だけ差し替えられる——それがこの構造の目的。
