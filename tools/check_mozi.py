#!/usr/bin/env python3
"""Check the Mohist text, chapter coverage, introductions and sentence hovers."""
import hashlib
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def soup(path):
    return BeautifulSoup(path.read_text(encoding="utf8"), "html.parser")


def main():
    witness = json.loads((ROOT / "sources/mozi/wikisource.json").read_text(encoding="utf8"))
    pages = witness["pages"]
    present = [p for p in pages if not p["missing"]]
    assert len(present) == 53 and len(pages) == 67
    assert sorted({p["volume"] for p in pages}) == list(range(1, 16))
    directory = soup(ROOT / "mozi/index.html")
    assert [h.get_text() for h in directory.select("h3.grp")] == [
        "卷" + build.cn(i) for i in range(1, 16)]
    assert [a["href"] for a in directory.select(".vols li.ok a")] == [
        p["slug"] + ".html" for p in present]
    assert [x.get_text() for x in directory.select(".vols li.todo")] == [
        p["title"] + "阙" for p in pages if p["missing"]]
    assert directory.select_one("header p.intro").get_text() == witness["intro"]
    assert directory.find("a", href="https://creativecommons.org/licenses/by-sa/4.0/")
    home = soup(ROOT / "index.html")
    card = home.select_one('#book-list a[href="mozi/index.html"]')
    assert card and card.select_one("p").get_text() == build.BOOK_INTRO["mozi"]
    assert card.select_one("p").get_text() != witness["intro"]
    translated = count = 0
    for p in present:
        slug = p["slug"]
        source = p["paragraphs"]
        assert hashlib.sha256("\n".join(source).encode()).hexdigest() == p["sha256"]
        sections = build.parse_poems(sorted((ROOT / "src/mozi" / slug).glob("*.txt")))
        assert len(sections) == 1 and sections[0]["title"] == p["title"]
        assert sections[0]["intro"], (slug, "missing title explanation")
        chunks = sections[0]["chunks"]
        assert "".join(c["o"] for c in chunks) == "".join(source), (slug, "source text changed")
        html = soup(ROOT / "mozi" / (slug + ".html"))
        assert "".join(x.get_text() for x in html.select(".entry p.v")) == "".join(source)
        expected = []
        for c in chunks:
            if c["t"] is None:
                continue
            parts = build.split_sents(c["o"])
            glosses = c["t"].split("¦")
            assert len(parts) == len(glosses) and all(x.strip() for x in glosses), slug
            expected.extend(zip(parts, glosses))
        assert [(x.get_text(), x["data-t"]) for x in html.select(".entry .s[data-t]")] == expected
        if all(c["t"] is not None for c in chunks):
            translated += 1
            assert any(c["notes"] for c in chunks), (slug, "no original notes")
        count += len(expected)
    assert f"{translated}/53" in directory.footer.get_text()
    print(f"OK: 15 volumes, 53 extant chapters, 14 catalogued lacunae, "
          f"{translated} fully annotated chapters, {count} sentence hovers")


if __name__ == "__main__":
    main()
