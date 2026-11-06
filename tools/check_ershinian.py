"""Verify Ershi Nian chapter coverage, full witness text, and verse formatting."""
from hashlib import sha256
import sys

from bs4 import BeautifulSoup

from prepare_ershinian import SLUG, ROOT, load, chapter_rows

sys.path.insert(0, str(ROOT))
from build import BOOK_INTRO, WIKI_INTRO


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    home = html("index.html")
    for slug, name in [(SLUG, "二十年目睹之怪现状")]:
        directory = html(f"{slug}/index.html")
        chapters = load(slug)
        keys = [f"p{n:03}" for n in range(1, 109)]
        assert [p["slug"] for p in chapters] == keys
        assert [a["href"] for a in directory.select("main li.ok a")] == [f"{key}.html" for key in keys]
        assert home.select_one(f'a[href="{slug}/index.html"] p').get_text() == BOOK_INTRO[slug]
        assert directory.select_one("p.intro").get_text() == WIKI_INTRO.get(slug, {}).get("text", BOOK_INTRO[slug])
        assert "维基文库" not in directory.get_text()
        count = 0
        for p in chapters:
            original = "".join(t for b in p["blocks"] for t in b["lines"])
            assert sha256(original.encode()).hexdigest() == p["sha256"]
            doc = html(f"{slug}/{p['slug']}.html")
            assert not doc.select("[data-t]") and "维基文库" not in doc.get_text()
            paragraphs = doc.select("section.entry p.v")
            assert "".join(t.get_text() for t in paragraphs) == original, (slug, p["slug"])
            assert [("诗" if "poem" in t["class"] else "原", t.get_text(separator="")) for t in paragraphs] == [
                (kind, text.replace("/", "")) for kind, text in chapter_rows(p)
            ], (slug, p["slug"])
            count += len(doc.select("p.poem"))
        print(f"《{name}》：一百零八回核验通过，居中诗联 {count} 处。")


if __name__ == "__main__":
    main()
