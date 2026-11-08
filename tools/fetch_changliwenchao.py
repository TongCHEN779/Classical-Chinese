#!/usr/bin/env python3
"""缓存维基文库茅坤《昌黎文钞》引与十六卷正文，写入 sources/changliwenchao/chapters.json。

  python3 tools/fetch_changliwenchao.py
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

BASE = ROOT / "sources/changliwenchao"


def clean(node):
    for x in node.select("span.variant-tooltip, sup.reference, style, link, ol.references, table, .noprint"):
        x.decompose()
    t = re.sub(r"\[\d+\]", "", node.get_text("", strip=False))
    return re.sub(r"\s+", " ", t).replace("　", "").replace("﻿", "").strip()


def blocks(root):
    for x in root.select("table, .licenseContainer, ol.references, ul, style, meta, link, #headerContainer"):
        x.decompose()
    for x in root.select("div.prose, div.poem, dl"):
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


# 原站该卷把这两篇嵌入的是同名消歧页，改取“（韩愈）”页的正文
DISAMBIG = {"潮州刺史谢上表": "潮州刺史謝上表 (韓愈)", "祭柳子厚文": "祭柳子厚文 (韓愈)"}


def article_paragraphs(title):
    page = fetch(title)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    return [t for lvl, t in blocks(root) if lvl == 0], str(page["revid"])


def parse_juan(n):
    page = fetch(f"昌黎文鈔/卷{n:02}")
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    head, sections, cur = "", [], None
    for lvl, t in blocks(root):
        if lvl == 1:
            head = t
        elif lvl >= 2:
            cur = {"title": t, "level": lvl, "path": [head], "author": "", "paragraphs": []}
            sections.append(cur)
        elif cur is not None:
            cur["paragraphs"].append(t)
    for sec in sections:
        if sec["title"] in DISAMBIG and any("可以指" in p for p in sec["paragraphs"]):
            sec["paragraphs"], _ = article_paragraphs(DISAMBIG[sec["title"]])
    sections = [s for s in sections if s["paragraphs"]]
    return {"slug": f"j{n:02}", "title": head or f"卷{n}", "url": "https://zh.wikisource.org/zh-hans/" + quote(f"昌黎文鈔/卷{n:02}"),
            "revision": str(page["revid"]), "heads": [], "sections": sections}


def parse_yin():
    page = fetch("昌黎文鈔引")
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    paras = [t for lvl, t in blocks(root) if lvl == 0]
    # 页面含两个版本：带标点的《昌黎文钞》引，与无标点的《茅鹿门先生文集》本；只取第一个
    cut = next((i for i, t in enumerate(paras) if t.startswith("《韩文公文钞》引")), len(paras))
    paras = paras[1:cut] if paras and paras[0].startswith("《昌黎文钞》引") else paras[:cut]
    return {"slug": "xu", "title": "引", "url": "https://zh.wikisource.org/zh-hans/" + quote("昌黎文鈔引"), "revision": str(page["revid"]),
            "heads": [], "sections": [{"title": "《昌黎文钞》引", "level": 2, "path": [], "author": "", "paragraphs": paras}]}


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    data = [parse_yin()] + [parse_juan(n) for n in range(1, 17)]
    for c in data:
        print(c["slug"], c["title"], len(c["sections"]), sum(len(s["paragraphs"]) for s in c["sections"]), sum(len(p) for s in c["sections"] for p in s["paragraphs"]), flush=True)
    (BASE / "chapters.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
