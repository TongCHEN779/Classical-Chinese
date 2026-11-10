"""核验只录原文的大书（tools/fetch_orig.py + tools/prepare_orig.py）：src 文本与页面正文逐段一致，目录与页面一一对应。"""
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
sys.path.insert(0, str(ROOT / "tools"))
from prepare_orig import ORIG_BOOKS


def main():
    paras = pages = 0
    for book in ORIG_BOOKS:
        if not (ROOT / "sources" / book / "pages.json").exists():
            continue
        plist = json.loads((ROOT / "sources" / book / "pages.json").read_text(encoding="utf8"))
        chapters = {c["slug"]: c for c in json.loads((ROOT / "sources" / book / "chapters.json").read_text(encoding="utf8"))}
        index = BeautifulSoup((BOOKS / book / "index.html").read_text(encoding="utf8"), "html.parser")
        assert [a["href"] for a in index.select("main li.ok a")] == [f"{p[0]}.html" for p in plist], book
        for slug, title, _g in plist:
            c = chapters[slug]
            want = [p for s in c["sections"] for p in s["paragraphs"]]
            txt = [l[2:] for l in (ROOT / "src" / book / slug / "01.txt").read_text(encoding="utf8").splitlines() if l.startswith("原：")]
            assert txt == want, (book, slug, "src 与 chapters.json 不一致")
            doc = BeautifulSoup((BOOKS / book / f"{slug}.html").read_text(encoding="utf8"), "html.parser")
            got = [p.get_text().strip() for p in doc.select("section.entry p.v")]
            assert got == [w.strip() for w in want], (book, slug, "页面与原文不一致")
            assert len(doc.select("section.entry")) == len(c["sections"]), (book, slug)
            assert not re.search(r"原文阅读版|白话与注释待整理|不设白话|原文直读", doc.get_text()), (book, slug)
            paras += len(want)
            pages += 1
    print(f"只录原文的大书核验通过：{pages} 页，{paras} 段。")


if __name__ == "__main__":
    main()
