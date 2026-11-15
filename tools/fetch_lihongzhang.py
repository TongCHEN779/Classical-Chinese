#!/usr/bin/env python3
"""缓存维基文库《李鸿章传》（梁启超，序例＋十二章）：写入 sources/lihongzhangzhuan/chapters.json 与 tables.json。

  python3 tools/fetch_lihongzhang.py [CACHE_DIR]     CACHE_DIR 里若已有 <标题>.json（API 原始返回，/ 换成 _）则不再联网

每章一页一节（节名即章名，序例同）；正文的 p、ul/li、blockquote、pre（按空行）、dl/dd 各作一段；
网页表格（兵力表、官员表等）不进 paragraphs，存入 tables.json，由 prepare_texts 插在指定段之后。
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_shihua import raw_page, para_text, cn

TITLES = ["序例", "第一章　绪论", "第二章　李鸿章之位置", "第三章　李鸿章未达以前及其时中国之形势", "第四章　兵家之李鸿章（上）",
          "第五章　兵家之李鸿章（下）", "第六章　洋务时代之李鸿章", "第七章　中日战争时代之李鸿章", "第八章　外交家之李鸿章（上）",
          "第九章　外交家之李鸿章（下）", "第十章　投闲时代之李鸿章", "第十一章　李鸿章之末路", "第十二章　结论"]


def clean(x):
    return re.sub(r"\s+", "", x.replace("　", ""))


def table_data(t):
    rows = []
    for tr in t.find_all("tr"):
        cells = [clean(c.get_text("")) for c in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells)
    cap = t.find("caption")
    return {"cap": clean(cap.get_text("")) if cap else "", "rows": rows, "has_th": bool(t.find("th"))}


def page_blocks(page):
    r = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    for x in r.select(".noprint, style, link, sup.reference, ol.references, .licenseContainer"):
        x.decompose()
    paras, tables = [], []
    for el in r.children:
        n = getattr(el, "name", None)
        if not n or n in ("style", "link", "div"):
            continue
        if n == "p":
            t = para_text(el)
            if t:
                paras.append(t)
        elif n == "ul":
            paras += [t for t in (para_text(li) for li in el.find_all("li", recursive=False)) if t]
        elif n == "blockquote":
            paras += [t for t in (para_text(p) for p in el.find_all("p")) if t]
        elif n == "pre":
            paras += [t for t in (clean(x) for x in re.split(r"\n\s*\n", el.get_text())) if t]
        elif n == "dl":
            paras += [t for t in (re.sub(r"[\s\u3000]+", " ", dd.get_text("")).strip() for dd in el.find_all("dd")) if t]
        elif n == "table":
            if "ws-header" in (el.get("class") or []) or "作者" in el.get_text() or not el.get_text(strip=True):
                continue
            d = table_data(el)
            d["after"] = len(paras) - 1
            tables.append(d)
    return paras, tables


def main():
    cache = sys.argv[1] if len(sys.argv) > 1 else None
    out, tbls = [], {}
    for i, title in enumerate(TITLES):
        wiki = f"李鴻章傳/{i:02d}"
        page = raw_page(wiki, cache)
        paras, tables = page_blocks(page)
        slug = f"z{i:02d}"
        out.append({"slug": slug, "title": title, "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(wiki), "revision": str(page["revid"]),
                    "heads": [], "sections": [{"title": title, "level": 3, "path": [title], "author": "", "paragraphs": paras}]})
        if tables:
            tbls[slug] = tables
        print(slug, len(paras), sum(len(p) for p in paras), len(tables), flush=True)
    d = ROOT / "sources/lihongzhangzhuan"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (d / "tables.json").write_text(json.dumps(tbls, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
