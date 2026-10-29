#!/usr/bin/env python3
"""
export_gate.py — 三層開示エンジンの保存前ゲート

保存前に facts/*.yaml を監査し、三層(Canon/Revealed/Belief)の関係が
説明可能かを検査する。違反があれば停止し、何が壊れているかを表示する。

検査項目（開示層 facts/*.yaml）:
  A. スキーマ健全性     — 必須フィールドの存在、status/bool の妥当性
  B. ラチェット不変条件 — revealed.status が前回保存から後退していないか
                          （＝開示の消失。ほぼLLMの記憶落ち事故）
  C. 乖離の正当性       — belief.diverges=true なら cause が非空か
                          （＝説明できない乖離＝ハルシネーションの温床）
  D. 開示のチャネル整合 — status>hidden なのに channel/at が空でないか
  E. 消失検出           — 前回開示済みの fact が今回消えていないか

検査項目（物質層 state.yaml。存在するときのみ）:
  F. 残高導出           — balances が Σ(history.delta) と一致するか（手書きdrift）
  G. 非負               — 残高に暗黙の負値がないか
  H. 在庫実在           — inventory の qty が正の整数か（不所持の消費/廃棄の検出）
  I. save_seq 単調      — meta.save_seq が前回保存から後退していないか
  J. 価格参照           — reason が price id を指す取引が amount×qty と一致するか
                          （＝記憶からの金額補完の検出。1銅貨→6銅貨事故の番人）
  K. id 一意            — prices/inventory/quests/npcs の id 重複

合格時: saves/last_revealed.json を更新し、CHANGELOG.md に [gate passed] を追記。
不合格時: 非ゼロ終了。スナップショットは更新しない。

エンジンは全キャンペーン共通。監査対象のキャンペーンは campaigns/<name>/ で選ぶ。

usage:
  python3 tools/export_gate.py <campaign>            # 指定キャンペーンを監査してコミット
  python3 tools/export_gate.py <campaign> --dry-run  # 監査のみ。書き込まない
  python3 tools/export_gate.py                       # campaigns/ に実キャンペーンが
                                                     #   1つだけならそれを自動選択
"""

import sys
import os
import json
import glob
import datetime

try:
    import yaml
except ImportError:
    sys.exit("PyYAML が必要です:  pip install pyyaml")

# --- ルート解決（このスクリプトの1つ上 = リポジトリのルート） ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPAIGNS_DIR = os.path.join(ROOT, "campaigns")


def list_campaigns():
    """campaigns/ 直下の実キャンペーン名（_ 始まりのテンプレは除外）。"""
    if not os.path.isdir(CAMPAIGNS_DIR):
        return []
    return sorted(
        d for d in os.listdir(CAMPAIGNS_DIR)
        if os.path.isdir(os.path.join(CAMPAIGNS_DIR, d)) and not d.startswith("_")
    )


def resolve_campaign(argv):
    """引数からキャンペーンを決める。無指定で実キャンペーンが1つなら自動選択。"""
    names = [a for a in argv[1:] if not a.startswith("-")]
    campaigns = list_campaigns()
    if names:
        name = names[0]
        path = os.path.join(CAMPAIGNS_DIR, name)
        if not os.path.isdir(path):
            avail = ", ".join(campaigns) or "(なし)"
            sys.exit(f"キャンペーン '{name}' が見つかりません。利用可能: {avail}\n"
                     f"新規作成:  cp -r campaigns/_template campaigns/{name}")
        return name
    if len(campaigns) == 1:
        return campaigns[0]
    if not campaigns:
        sys.exit("実キャンペーンがありません。\n"
                 "作成:  cp -r campaigns/_template campaigns/<name>")
    sys.exit("複数のキャンペーンがあります。名前を指定してください:\n  "
             + "\n  ".join(f"python3 tools/export_gate.py {c}" for c in campaigns))


# resolve_campaign() の結果で以下が確定する（main冒頭で設定）
CAMPAIGN = None
CAMPAIGN_DIR = None
FACTS_DIR = None
SAVES_DIR = None
SNAPSHOT = None
CHANGELOG = None
STATE_FILE = None


def bind_paths(campaign):
    global CAMPAIGN, CAMPAIGN_DIR, FACTS_DIR, SAVES_DIR, SNAPSHOT, CHANGELOG, STATE_FILE
    CAMPAIGN = campaign
    CAMPAIGN_DIR = os.path.join(CAMPAIGNS_DIR, campaign)
    FACTS_DIR = os.path.join(CAMPAIGN_DIR, "facts")
    SAVES_DIR = os.path.join(CAMPAIGN_DIR, "saves")
    SNAPSHOT = os.path.join(SAVES_DIR, "last_revealed.json")
    CHANGELOG = os.path.join(CAMPAIGN_DIR, "CHANGELOG.md")
    STATE_FILE = os.path.join(CAMPAIGN_DIR, "state.yaml")

STATUS_ORDER = {"hidden": 0, "partial": 1, "full": 2}

# ANSI（TTYのときだけ着色）
def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if sys.stdout.isatty() else s
RED = lambda s: _c("31", s)
GRN = lambda s: _c("32", s)
YEL = lambda s: _c("33", s)


class Violation:
    def __init__(self, fact_id, rule, msg):
        self.fact_id = fact_id
        self.rule = rule
        self.msg = msg

    def __str__(self):
        return f"  [{self.rule}] {self.fact_id}: {self.msg}"


def load_facts():
    """facts/*.yaml を読み、(facts_dict, load_errors) を返す。"""
    facts = {}
    errors = []
    for path in sorted(glob.glob(os.path.join(FACTS_DIR, "*.yaml"))):
        name = os.path.basename(path)
        if name.startswith("_"):          # _TEMPLATE.yaml 等はスキップ
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(Violation(name, "A-parse", f"YAML パース失敗: {e}"))
            continue
        if not isinstance(data, dict) or "id" not in data:
            errors.append(Violation(name, "A-parse", "id を持つマップではない"))
            continue
        fid = data["id"]
        expected = os.path.splitext(name)[0]
        if fid != expected:
            errors.append(Violation(fid, "A-id",
                          f"id '{fid}' がファイル名 '{expected}' と不一致"))
        facts[fid] = data
    return facts, errors


def check_schema(fid, fact):
    v = []
    if not fact.get("canon"):
        v.append(Violation(fid, "A-canon", "canon が空"))

    rev = fact.get("revealed")
    if not isinstance(rev, dict):
        v.append(Violation(fid, "A-revealed", "revealed ブロックが無い"))
        rev = {}
    status = rev.get("status")
    if status not in STATUS_ORDER:
        v.append(Violation(fid, "A-status",
                  f"status '{status}' が不正 (hidden/partial/full)"))

    bel = fact.get("belief")
    if not isinstance(bel, dict):
        v.append(Violation(fid, "A-belief", "belief ブロックが無い"))
        bel = {}
    if not isinstance(bel.get("diverges", False), bool):
        v.append(Violation(fid, "A-diverges", "belief.diverges が真偽値でない"))
    return v


def check_divergence(fid, fact):
    """C: diverges=true なら cause 必須（説明できない乖離の検出）。"""
    bel = fact.get("belief", {}) or {}
    if bel.get("diverges") is True:
        cause = bel.get("cause")
        if cause is None or str(cause).strip() == "":
            return [Violation(fid, "C-divergence",
                    "belief.diverges=true だが cause が空 "
                    "（説明できない乖離＝ハルシネーションの温床）")]
    return []


def check_channel(fid, fact):
    """D: 開示済み(status>hidden)なら channel と at が要る。"""
    rev = fact.get("revealed", {}) or {}
    status = rev.get("status")
    if status in ("partial", "full"):
        v = []
        if not str(rev.get("channel", "")).strip():
            v.append(Violation(fid, "D-channel",
                     f"status={status} だが channel が空 "
                     "（チャネルなき開示＝GM契約第1条違反）"))
        if not str(rev.get("at", "")).strip():
            v.append(Violation(fid, "D-at",
                     f"status={status} だが at(開示時刻) が空"))
        return v
    return []


def check_ratchet(facts, prev):
    """B & E: 前回スナップショットと比較して後退・消失を検出。"""
    v = []
    prev_revealed = prev.get("revealed", {})  # {fid: status}
    for fid, pstatus in prev_revealed.items():
        if STATUS_ORDER.get(pstatus, 0) == 0:
            continue  # 前回 hidden は追跡対象外
        if fid not in facts:
            v.append(Violation(fid, "E-vanished",
                     f"前回 status={pstatus} で開示済みだった fact が今回消えている "
                     "（開示の消失）"))
            continue
        now = (facts[fid].get("revealed") or {}).get("status", "hidden")
        if STATUS_ORDER.get(now, 0) < STATUS_ORDER.get(pstatus, 0):
            v.append(Violation(fid, "B-ratchet",
                     f"status が後退: {pstatus} → {now} "
                     "（ラチェット違反。開示は不可逆）"))
    return v


# ============================================================
#  物質状態台帳（state.yaml）の監査 — 検査 F〜K
#  state.yaml が無いキャンペーンは開示層のみ監査する（後方互換）。
# ============================================================

def load_state():
    """state.yaml を読む。無ければ (None, [])。壊れていれば (None, [violation])。"""
    if not os.path.exists(STATE_FILE):
        return None, []
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return None, [Violation("state.yaml", "S-parse", f"YAML パース失敗: {e}")]
    if not isinstance(data, dict):
        return None, [Violation("state.yaml", "S-parse", "マップではない")]
    return data, []


def _purse(state):
    return ((state.get("player") or {}).get("purse")) or {}


def _iter_history(state):
    return _purse(state).get("history") or []


def check_state_schema(state):
    """S: 最低限の構造（meta.clock と purse.history）。"""
    v = []
    if not str((state.get("meta") or {}).get("clock", "")).strip():
        v.append(Violation("state.yaml", "S-clock", "meta.clock が空"))
    if not isinstance(_purse(state).get("history", []), list):
        v.append(Violation("state.yaml", "S-purse", "player.purse.history が配列でない"))
    return v


def _sum_history(state):
    """通貨ごとの Σ delta。"""
    totals = {}
    for e in _iter_history(state):
        for unit, amt in (e.get("delta") or {}).items():
            if isinstance(amt, (int, float)):
                totals[unit] = totals.get(unit, 0) + amt
    return totals


def check_purse(state):
    """F: balances == Σ history。 G: 非負。"""
    v = []
    balances = _purse(state).get("balances") or {}
    totals = _sum_history(state)
    for unit in sorted(set(balances) | set(totals)):
        bal, tot = balances.get(unit, 0), totals.get(unit, 0)
        if bal != tot:
            v.append(Violation("state.yaml", "F-balance",
                     f"{unit}: balances={bal} が Σhistory={tot} と不一致（手書きdrift）"))
        if isinstance(bal, (int, float)) and bal < 0:
            v.append(Violation("state.yaml", "G-negative",
                     f"{unit}: 残高が負 ({bal})。借金は debt で明示せよ"))
    return v


def check_inventory(state):
    """H: 在庫 qty が正の整数（不所持の CONSUME/DROP は負値/欠落で現れる）。"""
    v = []
    for it in ((state.get("player") or {}).get("inventory")) or []:
        if not isinstance(it, dict):
            continue
        qty = it.get("qty")
        if not isinstance(qty, int) or qty <= 0:
            v.append(Violation("state.yaml", "H-inventory",
                     f"inventory[{it.get('id', '?')}]: qty={qty} が正の整数でない"))
    return v


def check_priced_history(state):
    """J: reason が price id を指す取引は |delta|==amount×qty と一致。"""
    v = []
    prices = {p.get("id"): p for p in (state.get("prices") or []) if isinstance(p, dict)}
    for e in _iter_history(state):
        p = prices.get(str(e.get("reason", "")).strip())
        if p is None:
            continue  # 価格id を指していない reason は対象外
        qty = e.get("qty", 1)
        if not isinstance(qty, int) or qty <= 0:
            v.append(Violation("state.yaml", "J-price",
                     f"reason={p.get('id')}: qty={qty} が正の整数でない"))
            continue
        unit = p.get("unit")
        got = abs((e.get("delta") or {}).get(unit, 0))
        expected = (p.get("amount") or 0) * qty
        if got != expected:
            v.append(Violation("state.yaml", "J-price",
                     f"reason={p.get('id')}: |delta[{unit}]|={got} が "
                     f"price({p.get('amount')})×qty({qty})={expected} と不一致"
                     "（記憶からの金額補完の疑い）"))
    return v


def check_state_ids(state):
    """K: 各リストの id 重複。"""
    v = []
    def dup(name, items):
        seen = set()
        for it in items or []:
            iid = it.get("id") if isinstance(it, dict) else None
            if iid is None:
                continue
            if iid in seen:
                v.append(Violation("state.yaml", "K-id", f"{name} で id 重複: {iid}"))
            seen.add(iid)
    dup("prices", state.get("prices"))
    dup("inventory", (state.get("player") or {}).get("inventory"))
    dup("quests", state.get("quests"))
    dup("npcs", state.get("npcs"))
    return v


def check_state_ratchet(state, prev):
    """I: meta.save_seq が前回スナップショットより後退していないか。"""
    prev_seq = (prev.get("state") or {}).get("save_seq")
    cur_seq = (state.get("meta") or {}).get("save_seq")
    if isinstance(prev_seq, int) and isinstance(cur_seq, int) and cur_seq < prev_seq:
        return [Violation("state.yaml", "I-seq",
                f"meta.save_seq が後退: {prev_seq} → {cur_seq}")]
    return []


def load_prev():
    if os.path.exists(SNAPSHOT):
        try:
            with open(SNAPSHOT, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print(YEL("警告: 既存スナップショットが読めない。初回として扱う。"))
    return {"revealed": {}}


def build_snapshot(facts, state=None):
    snap = {
        "revealed": {
            fid: (f.get("revealed") or {}).get("status", "hidden")
            for fid, f in facts.items()
        },
        "committed_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    if state is not None:
        snap["state"] = {
            "save_seq": (state.get("meta") or {}).get("save_seq"),
            "clock": (state.get("meta") or {}).get("clock"),
            "balances": _purse(state).get("balances") or {},
        }
    return snap


def revealed_delta(facts, prev):
    """今回新たに開示が進んだ数（ログ用）。"""
    prev_r = prev.get("revealed", {})
    k = 0
    for fid, f in facts.items():
        now = STATUS_ORDER.get((f.get("revealed") or {}).get("status"), 0)
        was = STATUS_ORDER.get(prev_r.get(fid, "hidden"), 0)
        if now > was:
            k += 1
    return k


def append_changelog(facts, delta):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[gate passed] {ts}  facts={len(facts)}  revealed_delta=+{delta}\n"
    with open(CHANGELOG, "a", encoding="utf-8") as f:
        f.write(line)


def main():
    dry = "--dry-run" in sys.argv
    bind_paths(resolve_campaign(sys.argv))
    print(f"キャンペーン: {CAMPAIGN}")
    facts, errors = load_facts()

    violations = list(errors)
    for fid, fact in facts.items():
        violations += check_schema(fid, fact)
        violations += check_divergence(fid, fact)
        violations += check_channel(fid, fact)

    prev = load_prev()
    violations += check_ratchet(facts, prev)

    # --- 物質状態台帳（state.yaml）の監査。無ければ開示層のみ ---
    state, state_errors = load_state()
    violations += state_errors
    if state is not None:
        violations += check_state_schema(state)
        violations += check_purse(state)
        violations += check_inventory(state)
        violations += check_priced_history(state)
        violations += check_state_ids(state)
        violations += check_state_ratchet(state, prev)

    state_line = "state.yaml なし（開示層のみ）" if state is None else "state.yaml あり"
    print(f"監査対象: {len(facts)} facts / {state_line}\n")

    if violations:
        print(RED(f"✗ ゲート停止: {len(violations)} 件の違反\n"))
        # ルール順にまとめて表示
        for v in sorted(violations, key=lambda x: x.rule):
            print(RED(str(v)))
        print("\n" + RED("保存は無効。上記を修正して再実行してください。"))
        print("スナップショットは更新していません。")
        sys.exit(1)

    delta = revealed_delta(facts, prev)
    print(GRN("✓ ゲート合格。三層の開示も物質台帳もすべて整合。"))
    print(f"  新規開示の進行: +{delta}")

    if dry:
        print(YEL("\n--dry-run: スナップショット/CHANGELOG は書き込みません。"))
        return

    os.makedirs(SAVES_DIR, exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(build_snapshot(facts, state), f, ensure_ascii=False, indent=2)
    append_changelog(facts, delta)
    print(f"\nスナップショット更新: {os.path.relpath(SNAPSHOT, ROOT)}")
    print(f"CHANGELOG 追記済み。")


if __name__ == "__main__":
    main()
