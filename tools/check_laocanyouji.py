"""Check the Lao Can You Ji original text and centered verse."""
from hashlib import sha256
import sys

from bs4 import BeautifulSoup

from prepare_laocanyouji import ROOT, originals, paragraphs, read
sys.path.insert(0, str(ROOT))
from build import BOOK_INTRO


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    entries = read("catalog.json")
    slugs = [e["slug"] for e in entries]
    assert slugs == ["xu", *(f"p{i:02}" for i in range(1, 21))]
    index = html("laocanyouji/index.html")
    assert [a["href"] for a in index.select("main li.ok a")] == [s + ".html" for s in slugs]
    intro = BOOK_INTRO["laocanyouji"]
    assert index.select_one("p.intro").get_text() == intro
    assert html("index.html").select_one('a[href="laocanyouji/index.html"] p').get_text() == intro
    verse = read("verse-blocks.json")
    total = 0
    for slug in slugs:
        raw = read(slug + ".json")
        assert sha256("\n".join(b["text"] for b in raw["blocks"]).encode()).hexdigest() == raw["text_sha256"]
        doc = html(f"laocanyouji/{slug}.html")
        assert not doc.select("[data-t]")
        assert "维基文库" not in doc.get_text()
        rows = doc.select("section.entry p.v")
        expected = list(paragraphs(slug))
        assert [(("诗" if "poem" in p["class"] else "原"), p.get_text()) for p in rows] == [
            (kind, text.replace("/", "")) for kind, text in expected], slug
        source = originals(slug)
        for block in reversed(verse.get(slug, [])):
            source.insert(block["before"], "".join(block["lines"]))
        assert "".join(p.get_text() for p in rows) == "".join(source), slug
        total += len(doc.select("p.poem"))
    assert "维基文库" not in index.get_text()
    print(f"《老残游记》自叙及二十回原文核验通过，居中诗联 {total} 处。")


if __name__ == "__main__":
    main()
