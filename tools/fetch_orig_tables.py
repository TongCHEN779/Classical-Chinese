#!/usr/bin/env python3
"""补抓只有表格、没有正文的页（宋史宰辅表、新唐书表、明史表、金史表等），把 wikitable 写入 chapters.json 对应节的 "tables"。

  python3 tools/fetch_orig_tables.py [book ...]
表格格式：{"cap": 标题, "head": [列名] 或 None, "rows": [[单元格…]]}；rowspan/colspan 占位处留空。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_orig import page_of, cut


def cell_text(c):
    for x in c.select("sup.reference, style"):
        x.decompose()
    return re.sub(r"\s+", " ", c.get_text(" ", strip=True)).replace(" ", "")


def grid(table):
    rows, pending = [], {}
    for tr in table.find_all("tr"):
        row, col = [], 0
        cells = tr.find_all(["th", "td"])
        is_head = bool(cells) and all(c.name == "th" for c in cells)
        it = iter(cells)
        while True:
            while col in pending and pending[col][0] > 0:
                row.append("")
                pending[col][0] -= 1
                col += 1
            c = next(it, None)
            if c is None:
                break
            rs, cs = int(c.get("rowspan", 1) or 1), int(c.get("colspan", 1) or 1)
            row.append(cell_text(c))
            for k in range(1, cs):
                row.append("")
            if rs > 1:
                for k in range(cs):
                    pending[col + k] = [rs - 1, 0]
            col += cs
        rows.append((is_head, row))
    return rows


def tables_of(root):
    out = []
    for t in root.find_all("table"):
        if "ws-header" in (t.get("class") or []) or len(t.find_all("tr")) < 3:
            continue
        g = grid(t)
        cap = t.find("caption")
        head = g[0][1] if g and g[0][0] else None
        body = [r for _h, r in (g[1:] if head else g) if any(r)]
        if body:
            out.append({"cap": cap.get_text(" ", strip=True) if cap else "", "head": head, "rows": body})
    return out


def main():
    books = sys.argv[1:] or ["songshi", "xintangshu", "mingshi", "jinshi"]
    for book in books:
        path = ROOT / "sources" / book / "chapters.json"
        chapters = json.loads(path.read_text(encoding="utf8"))
        n = 0
        for ch in chapters:
            if ch["sections"]:
                continue
            wiki = unquote(ch["url"].split("/zh-hans/", 1)[1])
            wiki, page, soup, frag = page_of(wiki)
            tbs = tables_of(soup.select_one(".mw-parser-output"))
            if tbs:
                ch["sections"] = [{"title": ch["title"], "level": 3, "path": [], "author": "", "paragraphs": [], "tables": tbs}]
                n += 1
            print(book, ch["slug"], ch["title"], len(tbs), sum(len(t["rows"]) for t in tbs), flush=True)
        path.write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print(book, "补表格", n, "页")


if __name__ == "__main__":
    main()
