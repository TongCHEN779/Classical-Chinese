"""Verify Guoyu coverage and exact sentence-level reading data."""
import sys
from bs4 import BeautifulSoup

from prepare_guoyu import ROOT, read

sys.path.insert(0, str(ROOT))
from build import BOOK_INTRO, WIKI_INTRO, parse_poems, split_sents


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    pages = read("catalog.json")
    slugs = ["xu", *(f"p{i:02}" for i in range(1, 22))]
    assert [p["slug"] for p in pages] == slugs
    index = html("guoyu/index.html")
    home = html("index.html")
    assert home.select_one('a[href="guoyu/index.html"] p').get_text() == BOOK_INTRO["guoyu"]
    assert "\n".join(p.get_text() for p in index.select("p.intro")) == WIKI_INTRO["guoyu"]["text"]
    assert [a["href"] for a in index.select("main li.ok a")] == [f"{s}.html" for s in slugs]
    total = done = notes = 0
    for slug in slugs:
        source = read(slug + ".json")["sections"]
        sections = parse_poems([ROOT / "src/guoyu" / slug / "01.txt"])
        assert [s["title"] for s in sections] == [s["title"] for s in source], slug
        assert all(s["intro"] for s in sections), slug
        paragraphs = [t for s in source for t in s["paragraphs"]]
        chunks = [c for s in sections for c in s["chunks"]]
        assert [c["o"] for c in chunks] == paragraphs, slug
        doc = html(f"guoyu/{slug}.html")
        rendered = doc.select("section.entry p.v")
        assert [p.get_text() for p in rendered] == paragraphs, slug
        for c, block in zip(chunks, rendered):
            originals = split_sents(c["o"])
            spans = block.select(".s[data-t]")
            total += len(originals)
            if c["t"] is not None:
                assert [s.get_text() for s in spans] == originals, slug
                assert [s["data-t"] for s in spans] == c["t"].split("¦"), slug
                done += len(spans)
            else:
                assert not spans, slug
        expected = [n for c in chunks for n in c["notes"]]
        assert [li.get_text() for li in doc.select(".notes.plain li")] == expected, slug
        assert [p.get_text() for p in doc.select(".intro-box p")] == [t for s in sections for t in s["intro"]], slug
        notes += len(expected)
    assert done == total, (done, total)
    print(f"《国语》二十一卷及解叙核验通过：{done}/{total}句白话，{notes}条注释。")


if __name__ == "__main__":
    main()
