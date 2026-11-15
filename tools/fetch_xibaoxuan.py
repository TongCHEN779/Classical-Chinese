#!/usr/bin/env python3
"""缓存维基文库《惜抱轩文集》（十六卷，嘉庆十二年粤秀书院重刻本）：写入 sources/xibaoxuan/chapters.json。

  python3 tools/fetch_xibaoxuan.py [CACHE_DIR]     CACHE_DIR 里若已有 <标题>.json（API 原始返回，/ 换成 _）则不再联网

页：序（姚原绂刻书缘起，取自总目页）与卷一至卷十六，页名取各卷一级标题（如“卷一·论”）；每篇（二级标题）为一节，
过长的篇按段落切开，节名“篇名·首段开头”。
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_shihua import raw_page, root_of, para_text, lead, group

G = 2300


def articles(page):
    root = root_of(page)
    title, arts, cur = None, [], None
    for el in root.children:
        if not getattr(el, "name", None):
            continue
        cls = el.get("class") or []
        if "mw-heading" in cls:
            h = el.find(re.compile("h[1-6]"))
            name = h.get_text(strip=True)
            if h.name == "h1":
                title = name
            else:
                cur = [name, []]
                arts.append(cur)
        elif el.name == "p" and cur is not None:
            t = para_text(el)
            if t:
                cur[1].append(t)
    return title, arts


def sections_of(arts, ptitle):
    secs = []
    for name, ps in arts:
        gs = group(ps, G)
        for g in gs:
            secs.append({"title": name if len(gs) == 1 else f"{name}·{lead(g[0])}", "level": 3, "path": [ptitle], "author": "", "paragraphs": g})
    return secs


def main():
    cache = sys.argv[1] if len(sys.argv) > 1 else None
    out = []
    main_page = raw_page("惜抱軒文集", cache)
    root = root_of(main_page)
    xu, cur = [], False
    for el in root.children:
        if not getattr(el, "name", None):
            continue
        cls = el.get("class") or []
        if "mw-heading" in cls:
            cur = el.get_text(strip=True) == "序"
        elif cur and el.name == "p":
            t = para_text(el)
            if t:
                xu.append(t)
    out.append({"slug": "x1", "title": "序", "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote("惜抱軒文集"),
                "revision": str(main_page["revid"]), "heads": [], "sections": [{"title": "序", "level": 3, "path": ["序"], "author": "", "paragraphs": xu}]})
    for n in range(1, 17):
        wiki = f"惜抱軒文集/卷{n:02d}"
        page = raw_page(wiki, cache)
        ptitle, arts = articles(page)
        secs = sections_of(arts, ptitle)
        out.append({"slug": f"j{n:02d}", "title": ptitle, "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(wiki),
                    "revision": str(page["revid"]), "heads": [], "sections": secs})
        print(f"j{n:02d}", ptitle, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
    d = ROOT / "sources/xibaoxuan"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("序", sum(len(p) for p in xu))


if __name__ == "__main__":
    main()
