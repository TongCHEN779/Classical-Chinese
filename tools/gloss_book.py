#!/usr/bin/env python3
"""只有原文页的书（如游仙窟）的逐句白话：列出各段切句、核对已写的白话。

  python3 tools/gloss_book.py show  BOOK PAGE [起 止)      列出第 起…止-1 段（编号同 build.py 的 overlay_gloss）及其切句
  python3 tools/gloss_book.py ranges BOOK PAGE N           按每份约 N 句，给出各段号区间
  python3 tools/gloss_book.py check BOOK PAGE [起 止)     核对 sources/BOOK/gloss/PAGE__*.json：句数对应、不缺段（给区间则只核对该区间）
白话写在 sources/BOOK/gloss/PAGE__起始段号.json，格式 {"start": 起始段号, "白话": ["句白话¦句白话", ...]}。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def chunks_of(book, page):
    secs = build.parse_poems(sorted((ROOT / "src" / book / page).glob("*.txt")))
    return [c for s in secs for c in s["chunks"] if "tbl" not in c]


def main():
    cmd, book, page = sys.argv[1:4]
    chunks = chunks_of(book, page)
    if cmd == "show":
        lo = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        hi = int(sys.argv[5]) if len(sys.argv) > 5 else len(chunks)
        for k in range(lo, min(hi, len(chunks))):
            sents = build.split_sents(chunks[k]["o"])
            print(f"[{k}]（{len(sents)} 句）" + " | ".join(sents))
    elif cmd == "ranges":
        n = int(sys.argv[4]); out, lo, cnt = [], 0, 0
        for k, c in enumerate(chunks):
            cnt += len(build.split_sents(c["o"]))
            if cnt >= n:
                out.append((lo, k + 1)); lo, cnt = k + 1, 0
        if lo < len(chunks):
            out.append((lo, len(chunks)))
        print(out)
    elif cmd == "check":
        got = {}
        for f in sorted((ROOT / "sources" / book / "gloss").glob(f"{page}__*.json")):
            d = json.loads(f.read_text(encoding="utf8"))
            for k, t in enumerate(d["白话"]):
                got[d["start"] + k] = t
        lo = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        hi = int(sys.argv[5]) if len(sys.argv) > 5 else len(chunks)
        problems = []
        for k, c in enumerate(chunks):
            if not lo <= k < hi:
                continue
            sents = build.split_sents(c["o"])
            if k not in got:
                problems.append(f"段{k}: 缺白话"); continue
            parts = got[k].split("¦")
            if len(parts) != len(sents) or not all(x.strip() for x in parts):
                problems.append(f"段{k}: 原文 {len(sents)} 句，白话 {len(parts)} 句")
            elif [o for o, _t in build.split_pairs(c["o"], got[k])] != sents:
                problems.append(f"段{k}: 会退回整段悬浮")
        got = {k: v for k, v in got.items() if lo <= k < hi}
        extra = sorted(set(got) - set(range(len(chunks))))
        if extra:
            problems.append(f"多出的段号 {extra[:5]}")
        print(book, page, "OK" if not problems else "有问题", f"（{len(got)}/{min(hi, len(chunks)) - lo} 段）")
        for p in problems[:30]:
            print("  -", p)
        sys.exit(1 if problems else 0)


main()
