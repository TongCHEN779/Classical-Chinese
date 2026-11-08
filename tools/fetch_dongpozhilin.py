#!/usr/bin/env python3
"""缓存维基文库《东坡志林》序与五卷正文，写入 sources/dongpozhilin/chapters.json。

  python3 tools/fetch_dongpozhilin.py
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch

BASE = ROOT / "sources/dongpozhilin"
CN = "零一二三四五"


def clean(node):
    for x in node.select("small, sup.reference, style, ol.references, table, .noprint"):
        x.decompose()
    t = re.sub(r"\[\d+\]", "", node.get_text("", strip=False))
    return re.sub(r"\s+", " ", t).replace("　", "").strip()


def blocks(root):
    """按顺序产出 (level, 标题) 或 (0, 段落)。"""
    for x in root.select("table, .licenseContainer, ol.references, ul, style, meta, link, #headerContainer"):
        x.decompose()
    for x in root.select("div.prose, div.poem, div.poem p, dl"):
        if x.name in ("div", "dl"):
            x.unwrap()
    for el in root.find_all(["div", "p"], recursive=False):
        if "mw-heading" in (el.get("class") or []):
            h = el.find(re.compile("h[1-6]"))
            yield int(h.name[1]), clean(h)
        elif el.name == "p":
            t = clean(el)
            if t:
                yield 0, t
        elif el.name == "div":
            for p in el.find_all(["p", "dd"]):
                t = clean(p)
                if t:
                    yield 0, t


def parse_juan(n):
    page = fetch(f"東坡志林/卷{CN[n]}")
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    cat, sections, cur = "", [], None
    for lvl, t in blocks(root):
        if lvl == 2:
            cat, cur = t, None
        elif lvl == 3:
            cur = {"title": t, "level": 3, "path": [cat], "author": "", "paragraphs": []}
            sections.append(cur)
        elif lvl == 0 and cur is not None and t != "东坡志林":
            cur["paragraphs"].append(t)
    sections = [s for s in sections if s["paragraphs"]]
    return {"slug": f"j{n}", "title": f"卷{CN[n]}", "url": "https://zh.wikisource.org/zh-hans/" + quote(f"東坡志林/卷{CN[n]}"),
            "revision": str(page["revid"]), "heads": [], "sections": sections}


def parse_xu():
    page = fetch("東坡志林")
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    sections, cur = [], None
    for lvl, t in blocks(root):
        if lvl == 2:
            cur = {"title": t, "level": 2, "path": [], "author": "", "paragraphs": []} if t == "序" else None
            if cur:
                sections.append(cur)
        elif lvl == 0 and cur is not None:
            cur["paragraphs"].append(t)
    return {"slug": "xu", "title": "序", "url": "https://zh.wikisource.org/zh-hans/" + quote("東坡志林"),
            "revision": str(page["revid"]), "heads": [], "sections": sections}


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    data = [parse_xu()] + [parse_juan(n) for n in range(1, 6)]
    for c in data:
        print(c["slug"], len(c["sections"]), sum(len(s["paragraphs"]) for s in c["sections"]), sum(len(p) for s in c["sections"] for p in s["paragraphs"]))
    (BASE / "chapters.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
