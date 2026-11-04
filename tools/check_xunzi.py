#!/usr/bin/env python3
"""Check the Xunzi catalog, source coverage, and rendered glosses."""
import hashlib
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def main():
    root = ROOT / "sources/xunzi"
    cat = read(root / "catalog.json")
    snapshot = read(root / "wikisource/index.json")
    assert cat["pages"] == snapshot["pages"] and cat["revision"] == snapshot["revision"]
    assert [x["slug"] for x in cat["pages"]] == ["xu"] + [f"p{i:02}" for i in range(1, 33)]
    assert sorted({x["volume"] for x in cat["pages"]}) == list(range(21))
    progress = read(root / "progress.json")
    done = {x["slug"]: x for x in progress["pages"]}
    assert progress["next"] == next((x["title"] for x in cat["pages"] if x["slug"] not in done), None)
    index = BeautifulSoup((ROOT / "xunzi/index.html").read_text(), "html.parser")
    assert index.select_one("p.intro").get_text() == snapshot["intro"]
    assert len(index.select(".vols > li")) == 33
    assert [a["href"] for a in index.select(".vols > li.ok a")] == [
        x["slug"] + ".html" for x in cat["pages"] if x["slug"] in done]
    home = BeautifulSoup((ROOT / "index.html").read_text(), "html.parser")
    for slug in ("liji", "shangshu", "xunzi"):
        page = BeautifulSoup((ROOT / slug / "index.html").read_text(), "html.parser")
        card = home.select_one(f'a[href="{slug}/index.html"] p')
        assert card.get_text() == build.BOOK_INTRO[slug]
        assert page.select_one("p.intro").get_text() == build.WIKI_INTRO[slug]["text"]
        assert card.get_text() != page.select_one("p.intro").get_text()
    for slug, meta in done.items():
        w = read(root / "wikisource" / f"{slug}.json")
        raw = [b["text"] for b in w["blocks"]]
        assert hashlib.sha256("\n".join(raw).encode()).hexdigest() == w["text_sha256"]
        assert hashlib.sha256("".join(raw).encode()).hexdigest() == meta["original_sha256"]
        assert meta["source"] == {k: w[k] for k in ("url", "revision")}
        sections = build.parse_poems(sorted((ROOT / "src/xunzi" / slug).glob("*.txt")))
        assert len(sections) == meta["sections"] and all(s["intro"] for s in sections)
        chunks = [c for s in sections for c in s["chunks"]]
        assert [c["o"] for c in chunks] == raw
        pairs = []
        for c in chunks:
            a, b = build.split_sents(c["o"]), c["t"].split("¦")
            assert len(a) == len(b) and all(x.strip() for x in b)
            pairs.extend(zip(a, (x.strip() for x in b)))
        page = BeautifulSoup((ROOT / "xunzi" / f"{slug}.html").read_text(), "html.parser")
        assert len(pairs) == meta["pairs"]
        assert [(x.get_text(), x["data-t"]) for x in page.select(".s[data-t]")] == pairs
        n = 0
        for button in page.select(".note-btn"):
            box = page.find(id=button["aria-controls"])
            assert box.has_attr("hidden")
            m = re.search(r"注释（(\d+)）", button.get_text())
            if m:
                assert len(box.find_all("li", recursive=False)) == int(m[1])
                n += int(m[1])
        assert n == meta["notes"] == sum(len(c["notes"]) for c in chunks)
        assert all(x.find_parent(attrs={"hidden": True})
                   for x in page.find_all("a", href=True) if build.is_wiki_source(x["href"]))
    print(f"OK: 荀子32篇及序，{len(done)}项已注译；三书首页与书内简介已核对")


if __name__ == "__main__":
    main()
