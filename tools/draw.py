#!/usr/bin/env python3
"""イベント抽選 — engine/event_draw.md の Python 実装。

使い方:
    python3 tools/draw.py <campaign> [--dry-run]

state.yaml の meta.move / meta.tension / meta.last_major_move を読み、
d20 を secrets で振って結果を判定し、CHANGELOG.md に DRAW 行を追記する。
state.yaml の meta は GM が結果どおりに上書きする（コメント保持のため本スクリプトは書き換えない）。
"""
import secrets
import sys
from pathlib import Path

import yaml

DEFAULT_TABLE = {"small_at": 16, "major_at": 20, "tension_cap": 5, "major_cooldown": 3}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry = "--dry-run" in sys.argv
    if not args:
        print("usage: draw.py <campaign> [--dry-run]")
        return 2
    root = Path(__file__).resolve().parent.parent / "campaigns" / args[0]
    state = yaml.safe_load((root / "state.yaml").read_text(encoding="utf-8"))
    meta = state.get("meta", {})
    table = {**DEFAULT_TABLE, **(meta.get("draw_table") or {})}

    move = int(meta.get("move", 0)) + 1  # この抽選は次の手のためのもの（開幕前は move=0）
    tension = min(int(meta.get("tension", 0)), table["tension_cap"])
    last_major = meta.get("last_major_move")

    r = secrets.randbelow(20) + 1
    total = r + tension
    if total >= table["major_at"]:
        tier = "major"
        if last_major is not None and move - int(last_major) <= table["major_cooldown"]:
            tier = "small"  # 大事件の連打を防ぐ格下げ
        if move == 1:
            tier = "small"  # 一手目は見渡し手。大は出さない
    elif total >= table["small_at"]:
        tier = "small"
    else:
        tier = "calm"
    new_tension = min(tension + 1, table["tension_cap"]) if tier == "calm" else 0

    clock = meta.get("clock", "")
    line = (f"DRAW  move={move}  d20={r}  tension={tension}  total={total}  "
            f"tier={tier}  at={clock}")
    print(line)
    print(f"→ state.meta を更新: move={move} tension={new_tension}"
          + (f" last_major_move={move}" if tier == "major" else ""))
    if tier != "calm":
        print(f"→ 事件を選んだら CHANGELOG に追記: EVENT  move={move}  id=<event_id>  tier={tier}")
    if not dry:
        with open(root / "CHANGELOG.md", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
