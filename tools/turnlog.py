#!/usr/bin/env python3
"""TURNLOG.md の解析と検索 — engine/turnlog.spec.md の Python 実装。

検索:
    python3 tools/turnlog.py <campaign> [--npc ID] [--fact ID] [--event ID]
                                        [--from N] [--to N] [--text 文字列]
条件は AND。該当する手のエントリをそのまま表示する。

export_gate.py からは parse() と check() を import して検査 L〜R に使う。
"""
import os
import re
import sys

KEYS = ["入力", "行為", "判定", "抽選", "事件", "起きたこと", "反応", "目撃", "噂", "新設定", "台帳", "開示"]
HEADER = re.compile(r"^### move (\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*$")
FIELD = re.compile(r"^- ([^:：]+)[:：]\s*(.*)$")
REF = re.compile(r"\b(npc|fact|ev|rumor):([A-Za-z0-9_]+)")
TIER = re.compile(r"^(calm|small|major)\b")
DRAW_LINE = re.compile(r"^DRAW\s+move=(\d+)\b.*?\btier=(calm|small|major)\b", re.MULTILINE)
EVENT_LINE = re.compile(r"^EVENT\s+move=(\d+)\s+id=([A-Za-z0-9_]+)", re.MULTILINE)
CANON_LINE = re.compile(r"^CANON\+\s+move=(\d+)\s+file=(\S+)", re.MULTILINE)
REGARD_LINE = re.compile(r"^ROLL\s+move=\d+\s+kind=(?:regard|hear)\s+npc=([A-Za-z0-9_]+)\b.*?\bafter=(-?\d+)", re.MULTILINE)
SPREAD_LINE = re.compile(r"^ROLL\s+move=\d+\s+kind=spread\s+rumor=([A-Za-z0-9_]+)\b.*?\breach=\d+→(\d+)", re.MULTILINE)
ACT_TAG = re.compile(r"(助ける|与える|果たす|敬う|寄進する|中立|無視する|茶化す|侮る|破る|欺く|奪う|脅す|害する)")
EMPTY = {"—", "-", "なし", ""}


def parse(text):
    """[{move, clock, place, fields{key: value}, raw, refs{kind: set}}] を返す。
    書式説明のコードブロック内は読まない。"""
    entries, cur, in_code = [], None, False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEADER.match(line)
        if m:
            cur = {"move": int(m.group(1)), "clock": m.group(2), "place": m.group(3),
                   "fields": {}, "raw": [line]}
            entries.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("## ") or line.startswith("---"):
            cur = None
            continue
        cur["raw"].append(line)
        f = FIELD.match(line)
        if f:
            cur["fields"][f.group(1).strip()] = f.group(2).strip()
    for e in entries:
        refs = {"npc": set(), "fact": set(), "ev": set(), "rumor": set()}
        for kind, rid in REF.findall("\n".join(e["raw"])):
            refs[kind].add(rid)
        e["refs"] = refs
        e["raw"] = "\n".join(e["raw"]).rstrip()
    return entries


def _event_ids(campaign_dir):
    path = os.path.join(campaign_dir, "world", "04_events.md")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return set(re.findall(r"^\|\s*(ev_[A-Za-z0-9_]+)\s*\|", f.read(), re.MULTILINE))


def check(campaign_dir, state, fact_ids):
    """検査 L/M/N/O。[(rule, msg)] を返す。TURNLOG.md が無ければ空。"""
    path = os.path.join(campaign_dir, "TURNLOG.md")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        entries = parse(f.read())
    out = []

    # L: 手番連続と meta.move
    for i, e in enumerate(entries, start=1):
        if e["move"] != i:
            out.append(("L-move", f"move {e['move']} の位置に move {i} が来るべき（欠番・重複・順序違い）"))
            break
    meta_move = ((state or {}).get("meta") or {}).get("move")
    if isinstance(meta_move, int) and meta_move > 0 and not entries:
        out.append(("L-move", f"meta.move={meta_move} なのに TURNLOG に手番エントリが無い（書式違いの可能性）"))
    if isinstance(meta_move, int) and entries and entries[-1]["move"] != meta_move:
        out.append(("L-move", f"TURNLOG の最後は move {entries[-1]['move']} だが meta.move={meta_move}"))

    # O: キー欠落
    for e in entries:
        missing = [k for k in KEYS if k not in e["fields"]]
        if missing:
            out.append(("O-keys", f"move {e['move']}: キー欠落 {', '.join(missing)}"))

    # M: 抽選照合
    cl_path = os.path.join(campaign_dir, "CHANGELOG.md")
    cl = open(cl_path, encoding="utf-8").read() if os.path.exists(cl_path) else ""
    draws = {int(m): t for m, t in DRAW_LINE.findall(cl)}
    events = {int(m): i for m, i in EVENT_LINE.findall(cl)}
    for e in entries:
        t = TIER.match(e["fields"].get("抽選", ""))
        if not t:
            continue  # 抽選しない手
        n, tier = e["move"], t.group(1)
        if n not in draws:
            out.append(("M-draw", f"move {n}: CHANGELOG に DRAW move={n} が無い"))
        elif draws[n] != tier:
            out.append(("M-draw", f"move {n}: TURNLOG は {tier}、CHANGELOG の DRAW は {draws[n]}"))
        if tier in ("small", "major"):
            evs = REF.findall(e["fields"].get("事件", ""))
            ev_ids = [rid for kind, rid in evs if kind == "ev"]
            if not ev_ids:
                out.append(("M-event", f"move {n}: {tier} なのに 事件 に ev:<id> が無い"))
            elif events.get(n) not in ev_ids:
                out.append(("M-event", f"move {n}: CHANGELOG の EVENT move={n} が無いか id が食い違う"))

    # P: 新設定 ⇔ CANON+ 行
    canon = {}
    for m, path_ in CANON_LINE.findall(cl):
        canon.setdefault(int(m), []).append(path_)
    for e in entries:
        n = e["move"]
        has_new = e["fields"].get("新設定", "—").strip() not in EMPTY
        if has_new and n not in canon:
            out.append(("P-canon", f"move {n}: 新設定 があるのに CHANGELOG に CANON+ move={n} が無い"))
        if not has_new and n in canon:
            out.append(("P-canon", f"move {n}: CHANGELOG に CANON+ move={n} があるのに 新設定 が「—」"))
    for n, paths in canon.items():
        for rel in paths:
            if not os.path.exists(os.path.join(campaign_dir, rel)):
                out.append(("P-canon", f"CANON+ move={n}: file={rel} が存在しない"))

    # Q: 好感照合（regard は最後の ROLL regard/hear の after と一致）
    npcs = {x.get("id"): x for x in ((state or {}).get("npcs") or []) if isinstance(x, dict)}
    last_after = {}
    for nid, after in REGARD_LINE.findall(cl):
        last_after[nid] = int(after)
    for nid, npc in npcs.items():
        rg = npc.get("regard")
        if rg is None:
            continue
        if not isinstance(rg, int) or not -3 <= rg <= 3:
            out.append(("Q-regard", f"npc:{nid}: regard={rg} が −3〜+3 の整数でない"))
        elif nid in last_after and last_after[nid] != rg:
            out.append(("Q-regard", f"npc:{nid}: regard={rg} だが最後の ROLL の after={last_after[nid]}"))

    # R: 噂の発生と伝播
    rumors = {r.get("id"): r for r in ((state or {}).get("rumors") or []) if isinstance(r, dict)}
    by_origin = {}
    for rid, r in rumors.items():
        by_origin.setdefault(r.get("origin_move"), []).append(rid)
    for e in entries:
        if "行為" not in e["fields"]:
            continue
        tags = ACT_TAG.findall(e["fields"].get("行為", ""))
        witnessed = e["fields"].get("目撃", "—").strip() not in EMPTY
        if witnessed and any(t != "中立" for t in tags) and e["move"] not in by_origin:
            out.append(("R-rumor", f"move {e['move']}: 目撃された中立以外の行為があるのに origin_move={e['move']} の噂が無い"))
    last_reach = {}
    for rid, reach in SPREAD_LINE.findall(cl):
        last_reach[rid] = int(reach)
    for rid, r in rumors.items():
        if rid in last_reach and r.get("reach") != last_reach[rid]:
            out.append(("R-rumor", f"rumor:{rid}: reach={r.get('reach')} だが最後の spread の結果は {last_reach[rid]}"))

    # N: 参照実在
    npc_ids = {x.get("id") for x in ((state or {}).get("npcs") or []) if isinstance(x, dict)}
    ev_ids = _event_ids(campaign_dir)
    for e in entries:
        for rid in sorted(e["refs"]["npc"] - npc_ids):
            out.append(("N-ref", f"move {e['move']}: npc:{rid} が state.yaml の npcs に無い"))
        for rid in sorted(e["refs"]["fact"] - set(fact_ids)):
            out.append(("N-ref", f"move {e['move']}: fact:{rid} が facts/ に無い"))
        for rid in sorted(e["refs"]["ev"] - ev_ids):
            out.append(("N-ref", f"move {e['move']}: ev:{rid} が world/04_events.md に無い"))
        for rid in sorted(e["refs"]["rumor"] - set(rumors)):
            out.append(("N-ref", f"move {e['move']}: rumor:{rid} が state.yaml の rumors に無い"))
    return out


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        return 2
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "campaigns", args[0], "TURNLOG.md")
    if not os.path.exists(path):
        sys.exit(f"{path} がありません")

    def opt(name):
        return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None

    with open(path, encoding="utf-8") as f:
        entries = parse(f.read())
    npc, fact, ev, text = opt("--npc"), opt("--fact"), opt("--event"), opt("--text")
    lo, hi = opt("--from"), opt("--to")
    hits = [e for e in entries
            if (npc is None or npc in e["refs"]["npc"])
            and (fact is None or fact in e["refs"]["fact"])
            and (ev is None or ev in e["refs"]["ev"])
            and (text is None or text in e["raw"])
            and (lo is None or e["move"] >= int(lo))
            and (hi is None or e["move"] <= int(hi))]
    for e in hits:
        print(e["raw"])
        print()
    print(f"-- {len(hits)} / {len(entries)} 手", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
