"""Verify Xuanzhenzi originals and sentence-level glosses in the generated site."""
from hashlib import sha256

from bs4 import BeautifulSoup

from prepare_xuanzhenzi import ROOT, VOLUMES, read
from build import BOOK_INTRO, parse_poems, split_sents


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    source = read("wikisource.json")
    assert sha256("\n".join(b["text"] for b in source["blocks"]).encode()).hexdigest() == source["text_sha256"]
    original = read("text.json")
    intro = BOOK_INTRO["xuanzhenzi"]
    index = html("xuanzhenzi/index.html")
    assert html("index.html").select_one('a[href="xuanzhenzi/index.html"] p').get_text() == intro
    assert index.select_one("p.intro").get_text() == intro
    assert [a["href"] for a in index.select("main li.ok a")] == ["p01.html", "p02.html", "p03.html"]
    total = notes = 0
    for i, (_, ids) in enumerate(VOLUMES, 1):
        slug = f"p{i:02}"
        doc = html(f"xuanzhenzi/{slug}.html")
        sections = parse_poems([ROOT / "src/xuanzhenzi" / slug / "001.txt"])
        chunks = [c for sec in sections for c in sec["chunks"]]
        paragraphs = doc.select("section.entry p.v")
        assert [p.get_text() for p in paragraphs] == [c["o"] for c in chunks] == [original[str(j)] for j in ids]
        assert doc.select_one(".intro-box p").get_text() == sections[0]["intro"][0]
        for c, paragraph in zip(chunks, paragraphs):
            spans = paragraph.select(".s[data-t]")
            assert [s.get_text() for s in spans] == split_sents(c["o"])
            assert [s["data-t"] for s in spans] == c["t"].split("¦")
            total += len(spans)
        expected = [n for c in chunks for n in c["notes"]]
        assert sorted(li.get_text() for li in doc.select(".notes.plain li")) == sorted(expected)   # 注释按正文上标顺序排列，故不比顺序
        notes += len(expected)
    print(f"《玄真子》三卷核验通过：{total}句白话，{notes}条注释。")


if __name__ == "__main__":
    main()
