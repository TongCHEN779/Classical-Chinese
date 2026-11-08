"""核验《昭明文选》：正文与维基文库快照逐段一致，逐句白话齐全，每节有题解。"""
import re
import sys
from bs4 import BeautifulSoup

from prepare_wenxuan import BASE, ROOT, read

sys.path.insert(0, str(ROOT))
from build import split_sents


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    chapters = read(BASE / "chapters.json")
    assert [c["slug"] for c in chapters] == ["xu", *(f"j{i:02}" for i in range(1, 61))]
    index = html("wenxuan/index.html")
    assert [a["href"] for a in index.select("main li.ok a")] == [f"{c['slug']}.html" for c in chapters]
    total = notes = 0
    for c in chapters:
        slug = c["slug"]
        paras = [p for s in c["sections"] for p in s["paragraphs"]]
        doc = html(f"wenxuan/{slug}.html")
        assert [p.get_text().strip() for p in doc.select("section.entry p.v")] == [p.strip() for p in paras], slug
        spans = doc.select("section.entry .s[data-t]")
        assert [s.get_text() for s in spans] == [x for p in paras for x in split_sents(p)], slug
        assert all(s["data-t"].strip() for s in spans), slug
        assert len(doc.select("section.entry")) == len(c["sections"]), slug
        assert all(e.select_one(".intro-box p") for e in doc.select("section.entry")), slug
        total += len(spans)
        notes += len(doc.select(".notes.plain li"))
    print(f"《昭明文选》核验通过：{total} 句白话，{notes} 条注释。")


if __name__ == "__main__":
    main()
