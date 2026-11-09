#!/usr/bin/env python3
"""补抓目录页上不在“书名/卷N”子页之下的序跋类单页（通典序、梁书目录序、金国语解、上明史表等），
作为 x1 页插到 chapters.json 的最前（front）或最后（back），并在 toc.json 记页名。

  python3 tools/fetch_orig_extra.py [book ...]
"""
import json
import sys
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_orig import page_of, items, units, sections, header_title

# book: (维基标题, 页名, front/back)
EXTRA = {
    "tongdian": ("通典序_（李翰）", "通典序（李翰）", "front"),
    "liangshu": ("梁書目錄序", "目录序", "front"),
    "weishu": ("舊本魏書目錄叙", "旧本魏书目录叙", "front"),
    "zhoushu": ("周書目錄序", "目录序", "front"),
    "xinwudaishi": ("五代史記序", "五代史记序", "front"),
    "jinshi": ("金國語解", "金国语解", "back"),
    "mingshi": ("上明史表", "上明史表", "front"),
}


def main():
    for book in sys.argv[1:] or list(EXTRA):
        wiki, title, where = EXTRA[book]
        path = ROOT / "sources" / book / "chapters.json"
        chapters = json.loads(path.read_text(encoding="utf8"))
        if any(c["slug"] == "x1" for c in chapters):
            continue
        wiki, page, soup, frag = page_of(wiki)
        root = soup.select_one(".mw-parser-output")
        seq = list(items(root))
        secs = sections(units(seq), title, 10 ** 7, False)
        ch = {"slug": "x1", "title": title, "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
              "revision": str(page["revid"]), "heads": [], "sections": secs}
        chapters = [ch] + chapters if where == "front" else chapters + [ch]
        path.write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        toc = ROOT / "sources" / book / "toc.json"
        d = json.loads(toc.read_text(encoding="utf8"))
        d[wiki] = title
        toc.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf8")
        print(book, title, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)


if __name__ == "__main__":
    main()
