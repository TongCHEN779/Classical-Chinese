#!/usr/bin/env python3
"""缓存《营造法式》的维基文库原文，写入 sources/yingzaofashi/chapters.json（只录原文）。
卷一至卷二十八用维基文库“营造法式”（带标点）；该本缺的卷二十九至卷三十四（图样卷）用“营造法式 (四庫全書本)”。
  python3 tools/fetch_yingzao.py
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_orig import page_of, items, num
from fetch_books2 import units, sections


def pages():
    out = [("x1", "劄子", "營造法式/劄子"), ("x2", "序", "營造法式/序"), ("x3", "看詳", "營造法式/看詳")]
    for n in range(1, 29):
        out.append((f"j{n:02}", None, f"營造法式/第{num(n)}卷"))
    for n in range(29, 35):
        out.append((f"j{n:02}", None, f"營造法式 (四庫全書本)/卷{n:02}"))
    return out


def main():
    res = []
    for slug, title, wiki in pages():
        wiki, p, soup, frag = page_of(wiki)
        root = soup.select_one(".mw-parser-output")
        seq = list(items(root))
        if title is None:                   # 卷名取页内一级标题“第一卷·总释上”，无则“卷N”
            n = int(slug[1:])
            head = next((t for l, t in seq if l == 1 and t.startswith("第")), "")
            title = f"卷{num(n)}" + ("·" + head.split("·", 1)[1] if "·" in head else "")
            if head:
                seq = [x for x in seq if x[1] != head]
        secs = sections(units(seq), title, 10 ** 7, False)
        res.append({"slug": slug, "title": title, "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
                    "revision": str(p["revid"]), "heads": [], "sections": secs})
        print(slug, title, len(secs), sum(len(q) for s in secs for q in s["paragraphs"]), flush=True)
        time.sleep(2)
    d = ROOT / "sources/yingzaofashi"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
