#!/usr/bin/env python3
"""WORKLOG と git 履歴の突き合わせ。

WORKLOG.md を作業ログの正本とし、git には各エントリを「Worklog: <見出し>」trailer 付きの
コミットとして残す。git の無い環境で WORKLOG だけ書き進めても、あとでこのスクリプトを
走らせれば、まだコミットに載っていないエントリと、そのためのコミットメッセージが得られる。

使い方:
    python3 tools/worklog_sync.py            # git に未記録のエントリを一覧
    python3 tools/worklog_sync.py --message  # 未記録エントリ用のコミットメッセージを出力
    git commit -F <(python3 tools/worklog_sync.py --message)
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2} — .+?)\s*$")
TRAILER = re.compile(r"^Worklog:\s*(.+?)\s*$", re.MULTILINE)


def parse_entries(text: str):
    """[(見出し, 本文)] を返す。書式説明のコードブロック内の見出しは拾わない。"""
    entries, current, body, in_code = [], None, [], False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        m = None if in_code else HEADING.match(line)
        if m:
            if current:
                entries.append((current, "\n".join(body)))
            current, body = m.group(1), []
        elif current:
            body.append(line)
    if current:
        entries.append((current, "\n".join(body)))
    return entries


def recorded_headings():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--all", "--format=%B"],
                             capture_output=True, text=True, check=True).stdout
        shallow = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
                                 capture_output=True, text=True).stdout.strip() == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("git リポジトリではないか、git がありません。WORKLOG だけ書き進め、git のある環境で再実行してください。")
    return set(TRAILER.findall(out)), shallow


def section(body: str, name: str) -> str:
    m = re.search(rf"^### {name}.*?$\n(.*?)(?=^### |\Z)", body, re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    # 2段目までの箇条だけ残して要約にする（折り返し行や3段目以降は落とす）
    keep = [l for l in m.group(1).splitlines() if l.startswith("- ") or l.startswith("  - ")]
    return "\n".join(keep).strip()


def main() -> int:
    entries = parse_entries((ROOT / "WORKLOG.md").read_text(encoding="utf-8"))
    done, shallow = recorded_headings()
    pending = [(h, b) for h, b in entries if h not in done]
    if shallow:
        print("注意: 浅いクローンです。古いコミットの trailer を見落として未記録と誤判定することがあります。",
              file=sys.stderr)

    if "--message" not in sys.argv:
        if not pending:
            print("WORKLOG の全エントリが git に記録済みです。")
        for h, _ in pending:
            print(f"未記録: {h}")
        return 0

    if not pending:
        print("未記録のエントリがありません。", file=sys.stderr)
        return 1
    titles = [h.split(" — ", 1)[1] for h, _ in pending]
    subject = titles[0] if len(titles) == 1 else f"{titles[0]} ほか WORKLOG {len(titles)}件"
    parts = [subject, ""]
    for h, b in pending:
        if len(pending) > 1:
            parts.append(f"■ {h}")
        changes = section(b, "変更")
        if changes:
            parts.append(changes)
        parts.append("")
    parts.append("詳細は WORKLOG.md の該当エントリを参照。")
    parts.append("")
    parts.extend(f"Worklog: {h}" for h, _ in pending)
    print("\n".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
