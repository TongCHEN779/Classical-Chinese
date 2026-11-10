#!/usr/bin/env python3
"""把 sources/<book>/chapters.json 切成注译作业：每个作业是某页的一段连续小节（原文约 MAX 字以内）。
  python3 tools/plan_jobs.py BOOK [MAX]        列出尚未完成的作业（页 起始节 结束节 字数），完成 = annotations/<页>__<起始节>.json 存在
  python3 tools/plan_jobs.py BOOK MAX --all    列出全部
作业输出：sources/<book>/annotations/<页>__<起始节>.json = {"start": 起始节, "items": [每节一项]}，格式见 tools/prepare_texts.py。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jobs(book, mx=4500):
    out = []
    for ch in json.loads((ROOT / "sources" / book / "chapters.json").read_text(encoding="utf8")):
        cur, size, start = [], 0, 0
        for i, s in enumerate(ch["sections"]):
            n = sum(len(p) for p in s["paragraphs"])
            if cur and size + n > mx:
                out.append((ch["slug"], start, i, size))
                cur, size, start = [], 0, i
            cur.append(i)
            size += n
        if cur:
            out.append((ch["slug"], start, len(ch["sections"]), size))
    return out


if __name__ == "__main__":
    book = sys.argv[1]
    mx = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 4500
    allj = "--all" in sys.argv
    adir = ROOT / "sources" / book / "annotations"
    todo = 0
    for slug, a, b, n in jobs(book, mx):
        done = (adir / f"{slug}__{a}.json").exists()
        if allj or not done:
            print(slug, a, b, n)
            todo += 1
    print("作业数", todo, file=sys.stderr)
