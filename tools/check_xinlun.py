"""Verify Xinlun coverage and exact sentence-level reading data."""
import sys
from bs4 import BeautifulSoup

from prepare_xinlun import OMIT, ROOT, read

sys.path.insert(0, str(ROOT))
from build import BOOK_INTRO, WIKI_INTRO, parse_poems, split_sents


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    pages = read("catalog.json")
    slugs = [f"p{i:02}" for i in range(1, 17)]
    assert [p["slug"] for p in pages] == slugs
    index = html("xinlun/index.html")
    home = html("index.html")
    assert home.select_one('a[href="xinlun/index.html"] p').get_text() == BOOK_INTRO["xinlun"]
    assert "\n".join(p.get_text() for p in index.select("p.intro")) == WIKI_INTRO["xinlun"]["text"]
    assert [a["href"] for a in index.select("main li.ok a")] == ["xu.html", *(f"{s}.html" for s in slugs), "appendix.html"]
    assert "维基文库" not in index.get_text()
    total = done = notes = 0
    for slug in slugs:
        source = read(slug + ".json")["sections"]
        sections = parse_poems([ROOT / "src/xinlun" / slug / "01.txt"])
        assert [s["title"] for s in sections] == [s["title"] for s in source], slug
        assert all(s["intro"] for s in sections), slug
        paragraphs = [t for s in source for i, t in enumerate(s["paragraphs"]) if i not in OMIT.get(slug, ())]
        chunks = [c for s in sections for c in s["chunks"]]
        assert [c["o"] for c in chunks] == paragraphs, slug
        doc = html(f"xinlun/{slug}.html")
        assert "维基文库" not in doc.get_text(), slug
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
    for slug in ("xu", "appendix"):
        source = read(f"{slug}-wikisource.json")["blocks"]
        doc = html(f"xinlun/{slug}.html")
        assert [p.get_text() for p in doc.select("section.entry p.v")] == [
            "".join(b["text"].splitlines()).strip() for b in source if not b["type"].startswith("h")
        ], slug
        paras = [t for b in source if not b["type"].startswith("h") for t in ["".join(b["text"].splitlines()).strip()]]
        spans = doc.select("section.entry .s[data-t]")
        assert [x.get_text() for x in spans] == [x for t in paras for x in split_sents(t)], slug
        assert all(x["data-t"].strip() for x in spans), slug
        total += len(spans)
        done += len(spans)
    assert done == total, (done, total)
    print(f"《新论》十六篇核验通过：{done}/{total}句白话，{notes}条注释。")


if __name__ == "__main__":
    main()
