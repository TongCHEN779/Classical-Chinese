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
        index = BeautifulSoup((ROOT / book / "index.html").read_text(), "html.parser")
        intro = build.WIKI_INTRO[book]
        snapshot = BeautifulSoup((sources / "wikisource/index.html.snapshot").read_text(), "html.parser")
        cell = snapshot.find(string=lambda part: part and part.startswith(intro["text"][:10])).parent
        text_parts = []
        for part in cell.contents:
            if part.name == "ul":
                break
            text_parts.append(part.get_text() if part.name else str(part))
        assert "".join(text_parts).strip() == intro["text"]
        assert index.select_one("p.intro").get_text() == intro["text"]
        assert index.find("a", href=intro["url"]) and index.find("a", href="https://creativecommons.org/licenses/by-sa/4.0/")
        if book == "liji":
            catalog = read(sources / progress["catalog"])["pages"]
            assert len(catalog) == 49 and catalog[0]["title"] == "曲礼上" and catalog[-1]["title"] == "丧服四制"
            for item in catalog:
                cached = read(sources / "wikisource" / f"{item['slug']}.json")
                assert cached["query"] == item["wiki"] and cached["revision"]
                witness = "\n".join(block["text"] for block in cached["blocks"])
                assert hashlib.sha256(witness.encode()).hexdigest() == cached["text_sha256"]
            slugs = [p["slug"] for p in catalog]
            assert [p["slug"] for p in done] == [s for s in slugs if s in {p["slug"] for p in done}]
            assert len(index.select(".vols > li")) == len(catalog)
            assert [a["href"] for a in index.select(".vols > li.ok a")] == [p["slug"] + ".html" for p in done]
            if "draft" in progress:
                draft = progress["draft"]
                source = read(sources / "wikisource" / (draft["slug"] + ".json"))
                assert source["revision"] == draft["revision"]
                offset = draft.get("next_sentence_offset", 0)
                block = source["blocks"][draft["next_source_block"]]["text"]
                sentences = build.split_sents(block)
                assert sentences[offset] == draft["next_text"]
                headings = draft.get("skipped_heading_blocks", [])
                assert sorted(draft["completed_source_blocks"] + headings) == list(range(draft["next_source_block"]))
                assert all(source["blocks"][i]["type"] == "h2" for i in headings)
                if offset:
                    assert "".join(sentences) == block
                sections = build.parse_poems([sources / draft["path"]])
                if headings:
                    expected_titles = [source["blocks"][i]["text"] for i in headings
                                       if i + 1 in draft["completed_source_blocks"] or
                                       (i + 1 == draft["next_source_block"] and offset)]
                    assert [e["title"] for e in sections] == expected_titles
                chunks = [c for e in sections for c in e["chunks"]]
                assert "".join(c["o"] for c in chunks) == "".join(
                    source["blocks"][i]["text"] for i in draft["completed_source_blocks"]) + "".join(sentences[:offset])
                assert all(len(build.split_sents(c["o"])) == len(c["t"].split("¦")) for c in chunks)
                assert sum(len(c["t"].split("¦")) for c in chunks) == draft["pairs"]
        else:
            catalog = read(sources / "catalog.json")
            assert len(catalog) == 58
            for item in catalog:
                cached = read(sources / "wikisource" / f"{item['slug']}.json")
                assert cached["query"] == item["wiki"] and cached["revision"]
                witness = "\n".join(block["text"] for block in cached["blocks"])
                assert hashlib.sha256(witness.encode()).hexdigest() == cached["text_sha256"]
            assert [p["slug"] for p in done] == [p["slug"] for p in catalog[:len(done)]]
            assert [h.get_text() for h in index.select("h3.grp")] == ["卷首", "虞书", "夏书", "商书", "周书"]
            assert len(index.select(".vols > li")) == len(catalog) + 1
            assert [a["href"] for a in index.select(".vols > li.ok a")] == [p["slug"] + ".html" for p in done]
            finished_titles = {p["slug"]: p["title"] for p in done}
            visible_titles = ["书序"] + [finished_titles.get(p["slug"], p["title"].split("，原文见", 1)[0]) for p in catalog]
            assert [item.find(["a", "span"], recursive=False).contents[0].strip()
                    for item in index.select(".vols > li")] == visible_titles

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
            if page.get("heading_blocks"):
                assert [e["title"] for e in entries] == [raw[i] for i in page["heading_blocks"]]
                assert sorted(page["heading_blocks"] + page["selected_blocks"]) == list(range(len(raw)))
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
