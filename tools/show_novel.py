"""列出白话小说某回的原文各段（编号仅供定位）：python3 tools/show_novel.py <书slug> <回号>   如 jinpingmei 001"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
book, slug = sys.argv[1], sys.argv[2]
j = -1
for f in sorted((ROOT / "src" / book / slug).glob("*.txt")):
    for ln in f.read_text(encoding="utf8").splitlines():
        if ln.startswith("# "):
            print(ln)
        elif ln[:2] in ("原：", "诗："):
            j += 1
            print(f"[{j}]{'(诗联)' if ln[:2] == '诗：' else ''} {ln[2:]}")
        elif ln.startswith(("注：", "注原：", "题解：")):
            print("    已有", ln)
