#!/usr/bin/env python3
"""Check the complete ctext transcription and its generated reading pages."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def main():
    dest = ROOT / "sources/canying"
    source = json.loads((dest / "ctext.json").read_text(encoding="utf8"))
    progress = json.loads((dest / "progress.json").read_text(encoding="utf8"))
    assert hashlib.sha256((dest / "ctext.html").read_bytes()).hexdigest() == source["html_sha256"]
    blocks = source["blocks"]
    assert [b["number"] for b in blocks] == list(range(1, 391))
    assert sum(len(b["source_comments"]) for b in blocks) == 632
    assert sum(len(b["missing_glyphs"]) for b in blocks) == 159
    assert sum(len(b["source_text"]) for b in blocks) == 61300
    raw_soup = BeautifulSoup((dest / "ctext.html").read_bytes(), "html.parser")
    raw_texts = []
    for row in raw_soup.select("tr.result"):
        cells = row.find_all("td", class_="ctext", recursive=False)
        if len(cells) == 2 and cells[0].get_text("", strip=True).isdecimal():
            raw_texts.append(cells[1].get_text("", strip=True))
    assert raw_texts == [b["source_text"] for b in blocks]
    seen = []
    annotated = []
    sentence_count = note_count = intro_count = 0
    for p in progress["pages"]:
        files = sorted((ROOT / "src/canying" / p["slug"]).glob("*.txt"))
        sections = build.parse_poems(files)
        expected = blocks[p["start"] - 1:p["end"]]
        assert len(sections) == len(expected) == 30
        expected_pairs = []
        for section, block in zip(sections, expected):
            assert len(section["chunks"]) == 1
            chunk = section["chunks"][0]
            assert chunk["o"] == block["reading_text"], block["number"]
            if chunk["t"] is not None:
                annotated.append(block["number"])
                raw = build.split_sents(chunk["o"])
                assert len(chunk["t"].split("¦")) == len(build._frag_groups(raw)), block["number"]
                pairs = build.split_pairs(chunk["o"], chunk["t"])
                assert len(pairs) == len(build._frag_groups(raw)), block["number"]
                expected_pairs.extend(pairs)
                sentence_count += len(pairs)
                note_count += len(chunk["notes"])
                intro_count += len(section["intro"])
                assert section["intro"] and chunk["notes"], block["number"]
        path = ROOT / "canying" / (p["slug"] + ".html")
        soup = BeautifulSoup(path.read_text(encoding="utf8"), "html.parser")
        assert [x.get_text() for x in soup.select("p.v")] == [b["reading_text"] for b in expected]
        assert len(soup.select("section.entry")) == 30
        spans = soup.select("[data-t]")
        assert [(span.get_text(), span["data-t"]) for span in spans] == expected_pairs
        assert "中国哲学书电子化计划" in soup.footer.get_text()
        assert "维基文库" not in soup.footer.get_text()
        if p.get("annotation_status") == "complete":
            assert len(expected_pairs) > 0
            assert all(c["t"] for s in sections for c in s["chunks"])
            assert "本句白话" in soup.select_one(".hint").get_text()
        else:
            assert not expected_pairs
            assert "白话译文与编者释义尚待整理" in soup.select_one(".hint").get_text()
        for a in soup.select("a[href]"):
            url = urlsplit(a["href"])
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert target.exists(), (path, a["href"])
            if url.fragment:
                target_soup = soup if target == path else BeautifulSoup(target.read_text(encoding="utf8"), "html.parser")
                assert target_soup.find(id=unquote(url.fragment)), (path, a["href"])
        for button in soup.select(".note-btn"):
            notes = soup.find(id=button["aria-controls"])
            assert notes is not None and notes.has_attr("hidden")
            if "注释" in button.get_text():
                assert f"（{len(notes.select('li'))}）" in button.get_text()
        ids = [x["id"] for x in soup.select("[id]")]
        assert len(ids) == len(set(ids)), path
        seen.extend(expected)
    assert seen == blocks
    assert annotated == progress.get("annotated_paragraphs", [])
    assert progress["annotation_counts"] == {"paragraphs": len(annotated), "sentence_pairs": sentence_count,
                                             "notes": note_count, "introductions": intro_count}
    assert len(list((ROOT / "src/canying").glob("*/*.txt"))) == 390
    assert "餐樱庑随笔" in (ROOT / "index.html").read_text(encoding="utf8")
    print(f"OK: 390 original paragraphs, {len(annotated)} annotated paragraphs, "
          f"{sentence_count} sentence pairs, {note_count} notes; source/HTML/link checks passed")


if __name__ == "__main__":
    main()
