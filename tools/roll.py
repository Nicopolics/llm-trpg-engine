#!/usr/bin/env python3
"""反応の機構 — engine/reaction.md の Python 実装。

    python3 tools/roll.py <campaign> regard <npc_id> <行為タグ> [--bystander]
    python3 tools/roll.py <campaign> check <易|並|難|至難> [--mod N]
    python3 tools/roll.py <campaign> spread
    python3 tools/roll.py <campaign> meet <npc_id>
    （どれも --dry-run で CHANGELOG に書かない。--move N で記録する手番を指定できる＝遡り処理用）

出目は secrets で振る。結果を CHANGELOG.md に ROLL 行として追記し、state.yaml に
書くべき値を表示する（state.yaml はコメント保持のため本スクリプトは書き換えない）。
手番は state.yaml の meta.move（draw.py の結果を反映した後の値）を使う。
"""
import os
import secrets
import sys

import yaml

CARES = ["金", "敬意", "体面", "秩序", "安全", "家族", "信仰", "自由"]
TAGS = {
    "助ける": {"安全": 1, "家族": 1},
    "与える": {"金": 1},
    "果たす": {"秩序": 1, "敬意": 1},
    "敬う": {"敬意": 1, "体面": 1},
    "寄進する": {"信仰": 1},
    "中立": {},
    "無視する": {"敬意": -1},
    "茶化す": {"敬意": -1, "体面": -1},
    "侮る": {"敬意": -1, "体面": -1},
    "破る": {"秩序": -1, "敬意": -1},
    "欺く": {"敬意": -1, "秩序": -1},
    "奪う": {"金": -1, "秩序": -1},
    "脅す": {"安全": -1, "自由": -1},
    "害する": {"安全": -1, "家族": -1},
}
STRONG = {"侮る", "害する"}
ESCALATE = {"茶化す": "侮る", "無視する": "侮る", "侮る": "脅す", "脅す": "害する", "欺く": "奪う"}
BANDS = {"易": 8, "並": 12, "難": 16, "至難": 20}


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def d(n):
    return secrets.randbelow(n) + 1


def compute_regard(npc, tag, bystander):
    """(hits, d6 or None, delta) を返す。"""
    if tag not in TAGS:
        sys.exit(f"未知の行為タグ: {tag}（使えるのは {' / '.join(TAGS)}）")
    weight = 2 if tag in STRONG else 1
    hits = [c for c in (npc.get("cares") or []) if c in TAGS[tag]]
    base = clip(sum(TAGS[tag][c] * weight for c in hits), -2, 2)
    if base == 0:
        return hits, None, 0
    r = d(6)
    delta = 0 if r == 1 else (clip(base * 2, -3, 3) if r == 6 else base)
    if bystander:
        delta = clip(delta, -1, 1)
    return hits, r, delta


def reaches(rumor, npc):
    reach = rumor.get("reach", 0)
    if reach >= 3:
        return True
    if reach >= 2 and npc.get("area") == rumor.get("area"):
        return True
    if reach >= 1 and npc.get("area") == rumor.get("area") and npc.get("spot") == rumor.get("spot"):
        return True
    return False


def main():
    argv = sys.argv[1:]
    args = [a for i, a in enumerate(argv)
            if not a.startswith("--") and not (i > 0 and argv[i - 1] in ("--mod", "--move"))]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2
    camp, cmd, rest = args[0], args[1], args[2:]
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "campaigns", camp)
    with open(os.path.join(root, "state.yaml"), encoding="utf-8") as f:
        state = yaml.safe_load(f)
    meta = state.get("meta") or {}
    move = meta.get("move", 0)
    if "--move" in sys.argv:  # 過去の手を遡って処理するとき（移行など）だけ使う
        move = int(sys.argv[sys.argv.index("--move") + 1])
    npcs = {n["id"]: n for n in (state.get("npcs") or []) if isinstance(n, dict)}
    lines, updates = [], []

    def npc_of(nid):
        if nid not in npcs:
            sys.exit(f"npc '{nid}' が state.yaml の npcs にありません")
        n = npcs[nid]
        if not isinstance(n.get("regard"), int):
            sys.exit(f"npc '{nid}' に regard（整数）がありません")
        return n

    if cmd == "regard":
        nid, tag = rest[0], rest[1]
        n = npc_of(nid)
        hits, r, delta = compute_regard(n, tag, "--bystander" in flags)
        before = n["regard"]
        after = clip(before + delta, -3, 3)
        lines.append(f"ROLL  move={move}  kind=regard  npc={nid}  tag={tag}  hits={','.join(hits) or '-'}  "
                     f"d6={r if r else '-'}  delta={delta:+d}  before={before}  after={after}")
        updates.append(f"npcs.{nid}.regard = {after}")

    elif cmd == "check":
        band = rest[0]
        if band == "自動":
            print("自動成功（振らない）。TURNLOG の判定に「自動」と書く。")
            return 0
        if band not in BANDS:
            sys.exit(f"難易度は 自動 / {' / '.join(BANDS)} のどれか")
        mod = 0
        if "--mod" in sys.argv:
            mod = int(sys.argv[sys.argv.index("--mod") + 1])
        r = d(20)
        total = r + mod
        ok = r == 20 or (r != 1 and total >= BANDS[band])
        lines.append(f"ROLL  move={move}  kind=check  band={band}  dc={BANDS[band]}  d20={r}  "
                     f"mod={mod:+d}  total={total}  result={'success' if ok else 'fail'}")

    elif cmd == "spread":
        for rm in state.get("rumors") or []:
            if rm.get("frozen") or rm.get("reach", 0) >= 3:
                continue
            r = d(6)
            bonus = 1 if rm.get("witnesses", 0) >= 3 else 0
            before = rm.get("reach", 0)
            after = before + 1 if r + bonus >= 4 else before
            tag = rm.get("tag")
            distorted = rm.get("distorted", False)
            if r == 1 and tag in ESCALATE:
                tag, distorted = ESCALATE[tag], True
            lines.append(f"ROLL  move={move}  kind=spread  rumor={rm['id']}  d6={r}  bonus={bonus}  "
                         f"reach={before}→{after}  distorted={str(distorted).lower()}  tag={tag}")
            updates.append(f"rumors.{rm['id']}: reach={after}  tag={tag}  distorted={str(distorted).lower()}")
        if not lines:
            print("広がる噂はありません。")
            return 0

    elif cmd == "meet":
        nid = rest[0]
        n = npc_of(nid)
        regard = n["regard"]
        for rm in state.get("rumors") or []:
            if nid in (rm.get("heard_by") or []) or not reaches(rm, n):
                continue
            hits, r, delta = compute_regard(n, rm.get("tag"), True)
            after = clip(regard + delta, -3, 3)
            lines.append(f"ROLL  move={move}  kind=hear  npc={nid}  rumor={rm['id']}  tag={rm.get('tag')}  "
                         f"hits={','.join(hits) or '-'}  d6={r if r else '-'}  delta={delta:+d}  "
                         f"before={regard}  after={after}")
            updates.append(f"rumors.{rm['id']}.heard_by に {nid} を追加")
            regard = after
        if not lines:
            print(f"{nid} に届いている未聴の噂はありません。")
            return 0
        updates.append(f"npcs.{nid}.regard = {regard}")
    else:
        print(__doc__)
        return 2

    for l in lines:
        print(l)
    for u in updates:
        print(f"→ state: {u}")
    if "--dry-run" not in flags:
        with open(os.path.join(root, "CHANGELOG.md"), "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
