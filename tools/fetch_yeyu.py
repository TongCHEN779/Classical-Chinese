#!/usr/bin/env python3
"""缓存维基文库《夜雨秋灯录》（清宣鼎，八卷，另有蔡尔康序、自序）：写入 sources/yeyuqiudenglu/chapters.json。

  python3 tools/fetch_yeyu.py [CACHE_DIR]     CACHE_DIR 里若已有 <标题>.json（API 原始返回，/ 换成 _）则不再联网

页：蔡尔康序、自序、卷一至卷八；卷内每篇（二级标题）为一节，节名即篇名，不再切分。续录另是一部书，这里不收。
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_shihua import raw_page, root_of, para_text, cn


def stories(page):
    secs, cur = [], None
    for el in root_of(page).children:
        if not getattr(el, "name", None):
            continue
        cls = el.get("class") or []
        if "mw-heading" in cls:
            cur = {"title": re.sub(r"\s+", "", el.get_text(strip=True)), "level": 3, "path": [], "author": "", "paragraphs": []}
            secs.append(cur)
        elif el.name == "p" and cur is not None:
            t = para_text(el)
            if t:
                cur["paragraphs"].append(t)
    return [s for s in secs if s["paragraphs"]]


def main():
    cache = sys.argv[1] if len(sys.argv) > 1 else None
    out = []
    for slug, title, wiki in [("x1", "蔡尔康序", "夜雨秋燈錄/蔡爾康序"), ("x2", "自序", "夜雨秋燈錄/自序")]:
        page = raw_page(wiki, cache)
        paras = []
        for el in root_of(page).children:
            if getattr(el, "name", None) == "p":
                t = para_text(el)
                if t:
                    paras.append(t)
        if paras and paras[0] == title:
            paras = paras[1:]
        out.append({"slug": slug, "title": title, "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(wiki), "revision": str(page["revid"]), "heads": [],
                    "sections": [{"title": title, "level": 3, "path": [title], "author": "", "paragraphs": paras}]})
    for n in range(1, 9):
        wiki = f"夜雨秋燈錄/卷{n}"
        page = raw_page(wiki, cache)
        secs = stories(page)
        for s in secs:
            s["path"] = [f"卷{cn(n)}"]
        out.append({"slug": f"j{n:02d}", "title": f"卷{cn(n)}", "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(wiki),
                    "revision": str(page["revid"]), "heads": [], "sections": secs})
        print(f"j{n:02d}", len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), max(sum(len(p) for p in s["paragraphs"]) for s in secs), flush=True)
    d = ROOT / "sources/yeyuqiudenglu"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    for c in out[:2]:
        print(c["title"], sum(len(p) for s in c["sections"] for p in s["paragraphs"]))


if __name__ == "__main__":
    main()
