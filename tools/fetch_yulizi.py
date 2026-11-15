#!/usr/bin/env python3
"""缓存维基文库《郁离子》（明成化六年《诚意伯文集》石刻本）：序与各则（共 180 则）。
维基文库目录页把各则分成五栏，按栏分页，每则为一节（节名即各则标题）。写入 sources/yulizi/chapters.json，页首提要并入 sources/wiki_intros.json。

  python3 tools/fetch_yulizi.py
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch

WIKI = "郁離子"
URL = "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(WIKI)


def paras(root):
    for x in root.select("table, style, .noprint, .licenseContainer, sup.reference, ol.references, #headerContainer"):
        x.decompose()
    out = []
    for p in root.find_all(["p", "dd", "div"], recursive=True):
        if p.find(["p", "dd", "div"]):
            continue
        t = re.sub(r"\s+", "", p.get_text("", strip=False)).replace("　", "")
        t = re.sub(r"〈[^〈〉]*〉", "", t)
        if t and not re.fullmatch(r"[←→]|郁离子/.*", t):
            out.append(t)
    return out


def main():
    page = fetch(WIKI)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    cols = [[(a.get_text(strip=True), urllib.parse.unquote(a["href"]).split("/wiki/")[1]) for a in td.select("li a")]
            for td in root.select("table.multicol td")]
    cols = [c for c in cols if c]
    head = [(a.get_text(strip=True), urllib.parse.unquote(a["href"]).split("/wiki/")[1]) for a in root.select("ul > li > a") if a.get_text(strip=True) == "序"][:1]
    groups = [("x1", "序", head)] + [(f"j{k}", f"{c[0][0]}至{c[-1][0]}", c) for k, c in enumerate(cols, 1)]
    out = []
    for slug, title, items in groups:
        secs = []
        for name, wiki in items:
            pg = fetch(wiki, retries=8)
            r = BeautifulSoup(pg["text"], "html.parser").select_one(".mw-parser-output")
            ps = paras(r)
            assert ps, wiki
            secs.append({"title": name, "level": 3, "path": [title], "author": "", "paragraphs": ps})
        out.append({"slug": slug, "title": title, "url": URL, "revision": str(page["revid"]), "heads": [], "sections": secs})
        print(slug, title, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
    d = ROOT / "sources/yulizi"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
