"""核验 tools/fetch_texts.py 抓取的各书：正文与维基文库快照逐段一致，逐句白话齐全，每节有题解。"""
import sys
from bs4 import BeautifulSoup

from prepare_texts import ROOT, TEXT_BOOKS, read, sent_units

sys.path.insert(0, str(ROOT))
from build import WIKI_INTRO, split_sents


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    total = notes = 0
    for book in TEXT_BOOKS:
        chapters = read(ROOT / "sources" / book / "chapters.json")
        index = html(f"{book}/index.html")
        single = len(chapters) == 1          # 只有一页的书：书的首页直接就是阅读页
        if single:
            assert not (ROOT / book / f"{chapters[0]['slug']}.html").exists(), f"{book} 不应再有独立的单页文件"
        else:
            assert [a["href"] for a in index.select("main li.ok a")] == [f"{c['slug']}.html" for c in chapters], book
        if WIKI_INTRO.get(book, {}).get("verbatim"):
            assert "\n".join(p.get_text() for p in index.select("p.intro")) == WIKI_INTRO[book]["text"], f"{book} 目录页简介应为维基文库原文"
        for c in chapters:
            paras = [p for s in c["sections"] for p in s["paragraphs"]]
            doc = index if single else html(f"{book}/{c['slug']}.html")
            assert [p.get_text().strip() for p in doc.select("section.entry p.v")] == [p.strip() for p in paras], (book, c["slug"])
            spans = doc.select("section.entry .s[data-t]")
            assert [s.get_text() for s in spans] == [x for p in paras for x in sent_units(p)], (book, c["slug"])
            assert all(s["data-t"].strip() for s in spans), (book, c["slug"])
            assert len(doc.select("section.entry")) == len(c["sections"]), (book, c["slug"])
            assert all(e.select_one(".intro-box p") for e in doc.select("section.entry")), (book, c["slug"])
            total += len(spans)
            notes += len(doc.select(".notes.plain li"))
    print(f"十二部短篇典籍核验通过：{total} 句白话，{notes} 条注释。")


if __name__ == "__main__":
    main()
