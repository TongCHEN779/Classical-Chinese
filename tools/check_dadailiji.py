"""Check Dadailiji source coverage, reading pages, and hover alignment."""
from hashlib import sha256

from bs4 import BeautifulSoup

from prepare_dadailiji import BASE, ROOT, extract, read
from build import BOOK_INTRO, parse_poems, split_sents


def page(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    catalog = read(BASE / "index.json")
    slugs = [p["slug"] for p in catalog["pages"]]
    assert slugs == [f"p{i:02}" for i in range(1, 41)]
    directory = page("dadailiji/index.html")
    assert directory.select_one("p.intro").get_text() == catalog["intro"]
    assert [a["href"] for a in directory.select(".vols li.ok a")] == [s + ".html" for s in slugs]
    card = page("index.html").select_one('a[href="dadailiji/index.html"] p')
    assert card.get_text() == BOOK_INTRO["dadailiji"] != catalog["intro"]
    pairs = notes = 0
    for slug in slugs:
        witness = read(BASE / f"{slug}.json")
        assert sha256("\n".join(b["text"] for b in witness["blocks"]).encode()).hexdigest() == witness["text_sha256"]
        originals = extract(slug)
        assert originals == read(BASE / "text" / f"{slug}.json")
        assert all("〈" not in t and "〉" not in t for t in originals)
        sections = parse_poems([ROOT / "src/dadailiji" / slug / "001.txt"])
        chunks = [c for section in sections for c in section["chunks"]]
        assert [c["o"] for c in chunks] == originals
        doc = page(f"dadailiji/{slug}.html")
        elements = doc.select("section.entry p.v")
        assert [p.get_text() for p in elements] == originals
        assert doc.select_one(".intro-box p"), slug
        for c, element in zip(chunks, elements):
            assert c["t"], (slug, c["o"][:24])
            spans = element.select("span.s[data-t]")
            assert [s.get_text() for s in spans] == split_sents(c["o"])
            assert [s["data-t"] for s in spans] == c["t"].split("¦")
            pairs += len(spans)
        expected = [n for c in chunks for n in c["notes"]]
        assert [li.get_text() for li in doc.select(".notes.plain li")] == expected
        notes += len(expected)
    print(f"《大戴礼记》40项校验通过：{pairs}句白话，{notes}条注释。")


if __name__ == "__main__":
    main()
