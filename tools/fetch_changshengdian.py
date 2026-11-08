#!/usr/bin/env python3
"""缓存维基文库洪昇《长生殿》五十出正文，写入 sources/changshengdian/chapters.json 与 progress.json。

  python3 tools/fetch_changshengdian.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch

BASE = ROOT / "sources/changshengdian"


def text_of(node):
    for x in node.select("sup.reference, style"):
        x.decompose()
    return re.sub(r"\[\d+\]", "", node.get_text("", strip=False)).replace("　", "").replace("﻿", "").strip()


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    toc = fetch("長生殿")
    root = BeautifulSoup(toc["text"], "html.parser").select_one(".mw-parser-output")
    titles = []
    for a in root.select("li a"):
        m = re.match(r"第(.+?)[齣出]\s*(.+)", a.get_text().replace("　", " ").strip())
        if m and re.search(r"/长生殿/\d\d|%E9%95%B7%E7%94%9F%E6%AE%BF/\d\d|长生殿/\d\d", (a.get("title") or "") + a["href"]):
            titles.append((a["href"], f"第{m.group(1)}出 {m.group(2).strip()}"))
    assert len(titles) == 50, len(titles)
    pages, progress = [], []
    for n in range(1, 51):
        page = fetch(f"長生殿/{n:02}")
        node = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
        for x in node.select("#headerContainer, table, .licenseContainer, style, meta, link, ol.references"):
            x.decompose()
        blocks = []
        for el in node.find_all(["p", "div"], recursive=False):
            if el.name == "p":
                t = text_of(el)
                if t:
                    blocks.append({"kind": "原", "text": t})
            elif "poem" in (el.get("class") or []):
                lines = [re.sub(r"\s+", "", x) for x in el.get_text("\n").split("\n")]
                lines = [x for x in lines if x]
                if lines:
                    blocks.append({"kind": "诗", "text": "/".join(lines)})
        title = titles[n - 1][1]
        slug = f"c{n:02}"
        url = "https://zh.wikisource.org/zh-hans/" + quote(f"長生殿/{n:02}")
        digest = hashlib.sha256("\n".join(b["text"] for b in blocks).encode("utf8")).hexdigest()
        pages.append({"slug": slug, "title": title, "url": url, "revision": str(page["revid"]), "blocks": blocks})
        progress.append({"slug": slug, "title": title, "sections": 1,
                         "source": {"title": f"長生殿/{n:02}", "url": url, "revision": str(page["revid"]), "text_sha256": digest}})
        print(slug, title, len(blocks), sum(len(b["text"]) for b in blocks), flush=True)
    (BASE / "chapters.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (BASE / "progress.json").write_text(json.dumps({"book": "长生殿", "pages": progress}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
