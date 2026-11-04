#!/usr/bin/env python3
"""Check cached original coverage, explicit glosses and rendered hovers."""
import hashlib
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def main():
    for book in ("shangshu", "liji"):
        sources = ROOT / "sources" / book
        progress = read(sources / "progress.json")
        done = [p for p in progress["pages"] if p["status"] == "complete"]
        if book == "liji":
            assert [p["slug"] for p in done] == ["daxue", "zhongyong"]
        else:
            catalog = read(sources / "catalog.json")
            assert len(catalog) == 58
            for item in catalog:
                cached = read(sources / "wikisource" / f"{item['slug']}.json")
                assert cached["query"] == item["wiki"] and cached["revision"]
                witness = "\n".join(block["text"] for block in cached["blocks"])
                assert hashlib.sha256(witness.encode()).hexdigest() == cached["text_sha256"]
            assert [p["slug"] for p in done] == [p["slug"] for p in catalog[:len(done)]]
        for page in done:
            slug = page["slug"]
            source = read(sources / "wikisource" / f"{slug}.json")
            raw = [b["text"] for b in source["blocks"]]
            assert hashlib.sha256("\n".join(raw).encode()).hexdigest() == source["text_sha256"]
            assert page["source"] == {k: source[k] for k in ("url", "revision")}
            witness = "".join(raw[i] for i in page.get("selected_blocks", range(len(raw))))
            if page.get("normalization") == "layout_line_breaks":
                witness = witness.replace("\n", "")
            assert hashlib.sha256(witness.encode()).hexdigest() == page["original_sha256"]
            entries = build.parse_poems(sorted((ROOT / "src" / book / slug).glob("*.txt")))
            assert len(entries) == page["sections"] and all(e["intro"] for e in entries)
            chunks = [c for e in entries for c in e["chunks"]]
            assert "".join(c["o"] for c in chunks) == witness, slug
            expected = []
            for c in chunks:
                original = build.split_sents(c["o"])
                modern = c["t"].split("¦")
                assert len(original) == len(modern) and all(t.strip() for t in modern), slug
                expected.extend(zip(original, (t.strip() for t in modern)))
            html = BeautifulSoup((ROOT / book / f"{slug}.html").read_text(), "html.parser")
            actual = [(s.get_text(), s["data-t"]) for s in html.select(".s[data-t]")]
            assert actual == expected and len(actual) == page["pairs"], slug
            assert sum(len(c["notes"]) for c in chunks) == page["notes"]
            for button in html.select(".note-btn"):
                target = html.find(id=button["aria-controls"])
                assert target.has_attr("hidden")
                if "注释" in button.get_text():
                    assert button.get_text(strip=True).endswith(f"注释（{len(target.find_all('li', recursive=False))}）")
        print(f"OK: {book}: {len(done)} completed pages, {sum(p['pairs'] for p in done)} hovers")


if __name__ == "__main__":
    main()
