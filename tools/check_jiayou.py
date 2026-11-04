#!/usr/bin/env python3
"""Check the 嘉祐集 witness, catalog, finished pages, and current draft."""
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
    source = ROOT / "sources/jiayou"
    witness = read(source / "wikisource/main.json")
    catalog = read(source / "catalog.json")
    progress = read(source / "progress.json")
    blocks = witness["blocks"]
    assert hashlib.sha256("\n".join(b["text"] for b in blocks).encode()).hexdigest() == witness["text_sha256"]
    assert catalog["revision"] == witness["revision"] == progress["source"]["revision"]
    pages = catalog["pages"]
    assert [p["slug"] for p in pages] == [f"juan{i:02}" for i in range(1, 17)] + ["buyi"]
    covered = []
    for p in pages:
        i = p["heading_block"]
        a, z = p["body_range"]
        assert a == i + 1 and blocks[i] == {"type": "h2", "text": p["title"]}
        assert p["entries"] == [dict(title=m[1], block=j, offset=m.start())
                                for j in range(a, z) for m in re.finditer(r"【([^】]+)】", blocks[j]["text"])]
        covered.extend(range(i, z))
    assert covered == list(range(len(blocks)))

    done = [p for p in progress["pages"] if p["status"] == "complete"]
    assert [p["slug"] for p in done] == [p["slug"] for p in pages[:len(done)]]
    html = BeautifulSoup((ROOT / "jiayou/index.html").read_text(), "html.parser")
    cells = html.select(".vols > li")
    assert len(cells) == 17
    assert [c.find(["a", "span"]).contents[0].strip() for c in cells] == [p["title"] for p in pages]
    assert [a["href"] for a in html.select(".vols li.ok a")] == [p["slug"] + ".html" for p in done]

    def audit_sections(sections, indices, count):
        chunks = [c for e in sections for c in e["chunks"]]
        assert all(e["intro"] and any(c["notes"] for c in e["chunks"]) for e in sections)
        assert [c["o"] for c in chunks] == [blocks[i]["text"] for i in indices]
        pairs = []
        for c in chunks:
            originals = build.split_sents(c["o"])
            translations = c["t"].split("¦")
            assert len(originals) == len(translations) and all(t.strip() for t in translations)
            pairs.extend(zip(originals, (t.strip() for t in translations)))
        assert len(pairs) == count
        return pairs, chunks

    for p, item in zip(done, pages, strict=False):
        sections = build.parse_poems(sorted((ROOT / "src/jiayou" / p["slug"]).glob("*.txt")))
        assert [e["title"] for e in sections] == [e["title"] for e in item["entries"]]
        a, z = item["body_range"]
        assert sorted(p["selected_blocks"] + [e["block"] for e in item["entries"]]) == list(range(a, z))
        pairs, chunks = audit_sections(sections, p["selected_blocks"], p["pairs"])
        assert hashlib.sha256("".join(c["o"] for c in chunks).encode()).hexdigest() == p["original_sha256"]
        html = BeautifulSoup((ROOT / "jiayou" / f"{p['slug']}.html").read_text(), "html.parser")
        assert [(s.get_text(), s["data-t"]) for s in html.select(".s[data-t]")] == pairs
        assert sum(len(c["notes"]) for c in chunks) == p["notes"]
        for button in html.select(".note-btn"):
            match = re.search(r"注释（(\d+)）", button.get_text())
            box = html.find(id=button["aria-controls"])
            assert box.has_attr("hidden")
            if match:
                assert len(box.find_all("li", recursive=False)) == int(match[1])
    if "draft" in progress:
        p = progress["draft"]
        item = next(x for x in pages if x["slug"] == p["slug"])
        sections = build.parse_poems([source / p["path"]])
        a, _ = item["body_range"]
        assert sorted(p["selected_blocks"] + p["heading_blocks"]) == list(range(a, p["next_heading_block"]))
        assert [f"【{s['title']}】" for s in sections] == [blocks[i]["text"] for i in p["heading_blocks"]]
        assert blocks[p["next_heading_block"]]["text"] == f"【{progress['next']['title']}】"
        audit_sections(sections, p["selected_blocks"], p["pairs"])
        assert not (ROOT / "jiayou" / f"{p['slug']}.html").exists()
    home = BeautifulSoup((ROOT / "index.html").read_text(), "html.parser")
    assert home.find("a", href="jiayou/index.html").find("strong").get_text() == "嘉祐集"
    print(f"OK: 嘉祐集17项目录，{len(done)}项已注译；底本、白话和接续位置一致")


if __name__ == "__main__":
    main()
