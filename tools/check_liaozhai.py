#!/usr/bin/env python3
"""Check completed Wikisource entries against snapshots and rendered sentence pairs."""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.anchors, self.translations = [], [], []
        self.buttons, self.lists = [], {}
        self.button, self.note_list, self.label = None, None, ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and a.get("href", "").startswith("#"):
            self.anchors.append(a["href"][1:])
        if "data-t" in a:
            self.translations.append(a["data-t"])
        if tag == "button" and "note-btn" in a.get("class", "").split():
            self.button, self.label = a["aria-controls"], ""
        if tag in ("ul", "ol") and "notes" in a.get("class", "").split():
            self.note_list = a["id"]
            self.lists[self.note_list] = 0
        if tag == "li" and self.note_list:
            self.lists[self.note_list] += 1

    def handle_data(self, data):
        if self.button:
            self.label += data

    def handle_endtag(self, tag):
        if tag == "button" and self.button:
            count = re.search(r"注释（(\d+)）", self.label)
            if count:
                self.buttons.append((self.button, int(count[1])))
            self.button = None
        if tag in ("ul", "ol"):
            self.note_list = None


def source_entries(snapshot):
    sections, title = {}, None
    for block in snapshot["blocks"]:
        if block["type"] in ("h2", "h3"):
            title = block["text"]
            assert title not in sections, title
            sections[title] = []
        elif block["type"] == "p" and title:
            sections[title].append(block["text"].replace("\n", ""))
    return sections


def check_volume(volume):
    slug = f"juan{volume['volume']:02d}"
    completed = [e for e in volume["entries"] if e["status"] == "complete"]
    if volume["status"] == "complete":
        assert len(completed) == len(volume["entries"])
    elif volume["status"] == "pending":
        assert not completed
    expected, checked, paragraphs, sentences, notes = [], [], 0, 0, 0
    for entry in completed:
        path = ROOT / "src/liaozhai" / slug / f"{entry['id']}.txt"
        sections = build.parse_poems([path])
        assert len(sections) == 1 and sections[0]["title"] == entry["title"], path
        section = sections[0]
        assert section["intro"]
        expected.extend(t for c in section["chunks"] for _, t in build.split_pairs(c["o"], c["t"]))
        review = entry.get("review", {})
        if review.get("source") != "wikisource":
            continue
        source = json.loads((ROOT / review["snapshot"]).read_text())
        originals = source_entries(source)[review.get("source_title", entry["title"])]
        assert [c["o"] for c in section["chunks"]] == originals, path
        p, s, n = len(originals), 0, 0
        for chunk in section["chunks"]:
            count = len(build.split_sents(chunk["o"]))
            assert count == len(chunk["t"].split("¦")), path
            assert count == len(build.split_pairs(chunk["o"], chunk["t"])), path
            s += count
            n += len(chunk["notes"])
        for line in path.read_text().splitlines():
            if line.startswith("注："):
                assert len(build.split_notes(line[2:])) == 1, (path, line)
        assert (p, s, n) == (review["paragraphs"], review["sentence_pairs"], review["notes"]), path
        paragraphs, sentences, notes = paragraphs + p, sentences + s, notes + n
        checked.append(entry["title"])
    if completed:
        reader = Reader()
        reader.feed((ROOT / "liaozhai" / f"{slug}.html").read_text())
        assert reader.translations == expected, slug
        assert len(reader.ids) == len(set(reader.ids)), slug
        assert len(reader.anchors) == len(completed), slug
        assert set(reader.anchors) <= set(reader.ids), slug
    catalog = volume.get("catalog_source")
    if catalog:
        source = json.loads((ROOT / catalog["snapshot"]).read_text())
        assert [e["title"] for e in volume["entries"]] == list(source_entries(source)), slug
    return {"volume": volume["volume"], "wiki_entries_checked": len(checked),
            "paragraphs": paragraphs, "sentence_pairs": sentences, "notes": notes,
            "source_coverage_and_rendered_translations_match": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    progress = json.loads((ROOT / "sources/liaozhai/progress.json").read_text())
    volumes = [check_volume(v) for v in progress["volumes"]]
    preface = progress.get("preface_review")
    if progress["preface_status"] == "complete" and preface:
        section = build.parse_poems([ROOT / "src/liaozhai/zizhi/001.txt"])[0]
        source = json.loads((ROOT / preface["snapshot"]).read_text())
        assert section["chunks"][0]["o"] == source["blocks"][0]["text"]
        reader = Reader()
        reader.feed((ROOT / "liaozhai/zizhi.html").read_text())
        assert reader.translations == section["chunks"][0]["t"].split("¦")
    page_count, button_count = 0, 0
    for path in ROOT.rglob("*.html"):
        if any(p.startswith(".") for p in path.relative_to(ROOT).parts):
            continue
        reader = Reader()
        reader.feed(path.read_text())
        page_count += 1
        for target, count in reader.buttons:
            assert reader.lists.get(target) == count, (path, target, count)
            button_count += 1
    result = {"volumes": volumes, "all_site_html_pages": page_count,
              "all_site_note_buttons": button_count, "all_note_counts_match": True,
              "browser_visual_check": False, "next": progress.get("next")}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
