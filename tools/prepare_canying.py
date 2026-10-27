#!/usr/bin/env python3
"""Prepare the user-selected ctext edition without silently correcting its text.

Usage: python3 tools/prepare_canying.py /path/to/downloaded.html
The HTML must be the simplified chapter=924437 page, not Wikisource's mislabelled book.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
URL = "https://ctext.org/wiki.pl?chapter=924437&if=gb&remap=gb"


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main(path):
    # A source refresh must not destroy independently written translations/notes.
    for edited in (ROOT / "src/canying").glob("*/*.txt"):
        if "||" in edited.read_text(encoding="utf8"):
            raise SystemExit("已有译注稿，停止原文初始化以防覆盖。请保留译注并单独核对底本更新。")
    raw = Path(path).read_bytes()
    soup = BeautifulSoup(raw, "html.parser")
    blocks = []
    for row in soup.select("tr.result"):
        cells = row.find_all("td", class_="ctext", recursive=False)
        if len(cells) != 2:
            continue
        number = cells[0].get_text("", strip=True)
        if not number.isdecimal():
            continue
        cell = cells[1]
        original = cell.get_text("", strip=True)
        comments = [x.get_text("", strip=True) for x in cell.select(".inlinecomment")]
        # These are existing source annotations, not newly written notes.
        # Wrapping the nodes preserves both their position and their full text.
        for node in reversed(cell.select(".inlinecomment")):
            node.insert_before("（")
            node.insert_after("）")
        text = cell.get_text("", strip=True)
        missing = [{"offset": i, "codepoint": f"U+{ord(c):04X}"}
                   for i, c in enumerate(text) if 0xE000 <= ord(c) <= 0xF8FF]
        readable = re.sub(r"[\ue000-\uf8ff]", "〔缺字〕", text)
        blocks.append({"number": int(number), "source_anchor": row.get("id"),
                       "source_text": original, "text_with_comment_brackets": text,
                       "reading_text": readable, "source_comments": comments,
                       "missing_glyphs": missing})
    assert [b["number"] for b in blocks] == list(range(1, 391)), "Unexpected source paragraph sequence"
    assert blocks[0]["source_text"].startswith("清制：凡荫生")
    assert blocks[-1]["source_text"].startswith("康熙朝，宛平黄昆圃叔琳")
    dest = ROOT / "sources/canying"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "ctext.html").write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    save(dest / "ctext.json", {"title": "餐樱庑随笔", "author": "况周颐", "url": URL,
                               "retrieved_on": "2026-10-27", "html_sha256": digest,
                               "edition": "User-selected ctext chapter 924437, simplified display",
                               "blocks": blocks})
    pages = []
    for start in range(0, len(blocks), 30):
        group = blocks[start:start + 30]
        slug = f"part{start // 30 + 1:02d}"
        directory = ROOT / "src/canying" / slug
        directory.mkdir(parents=True, exist_ok=True)
        for block in group:
            n = block["number"]
            # Paragraph numbers belong to ctext; they are not original chapter numbers.
            lead = re.sub(r"[《》「」『』：，。；、（）〔〕！？」？\s]", "", block["reading_text"])[:12]
            lines = [f"# {n:03d}｜{lead}", "原：" + block["reading_text"]]
            if block["missing_glyphs"]:
                lines.append("注：缺字：本段原站含旧字库字符，现以〔缺字〕逐字标出；字形尚待核定，不据上下文猜补。")
            (directory / f"{n:03d}.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
        pages.append({"slug": slug, "title": f"第{start + 1:03d}—{start + len(group):03d}段",
                      "start": group[0]["number"], "end": group[-1]["number"],
                      "source": {"url": URL, "label": "中国哲学书电子化计划",
                                 "after": "2026年10月27日采集。"}})
    missing_blocks = [b for b in blocks if b["missing_glyphs"]]
    save(dest / "progress.json", {"title": "餐樱庑随笔", "author": "况周颐",
         "source_url": URL, "source_html_sha256": digest,
         "original_status": "complete_transcription_of_selected_web_edition",
         "collation_status": "not_collated_against_scan",
         "translation_status": "not_started", "editorial_annotation_status": "missing_glyph_notices_only",
         "source_paragraphs": len(blocks), "source_inline_comments": sum(len(b["source_comments"]) for b in blocks),
         "source_characters": sum(len(b["source_text"]) for b in blocks),
         "missing_glyph_count": sum(len(b["missing_glyphs"]) for b in blocks),
         "missing_glyph_paragraphs": [b["number"] for b in missing_blocks],
         "pages": pages})
    print(f"{len(blocks)} paragraphs, {len(pages)} pages, "
          f"{sum(len(b['source_comments']) for b in blocks)} source comments, "
          f"{sum(len(b['missing_glyphs']) for b in blocks)} missing glyphs")


if __name__ == "__main__":
    main(sys.argv[1])
