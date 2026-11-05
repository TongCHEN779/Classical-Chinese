"""Build the original-only reading tails and progress from the pinned Yili text."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import has_sentence_pairs, parse_poems, split_sents

BASE = ROOT / "sources/yili"
chapters = json.loads((BASE / "chapters.json").read_text())
reading = json.loads((BASE / "chapters-simplified.json").read_text())
assert len(chapters) == 17
progress = []
for chapter in chapters:
    slug, title, originals = (chapter[key] for key in ("slug", "title", "paragraphs"))
    assert chapter["revision"] and originals, slug
    simplified = reading[slug]
    assert len(simplified) == len(originals), slug
    originals = simplified
    folder = ROOT / "src/yili" / slug
    draft = folder / "01.txt"
    sections = parse_poems([draft]) if draft.exists() else []
    chunks = [c for section in sections for c in section["chunks"]]
    count = len(chunks)
    assert [c["o"] for c in chunks] == originals[:count], slug
    assert all(has_sentence_pairs(c) for c in chunks), slug
    remaining = originals[count:]
    tail = folder / "02-original.txt"
    if remaining:
        folder.mkdir(parents=True, exist_ok=True)
        heading = "后续原文（待注译）" if count else title
        tail.write_text(f"# {heading}\n" + "".join(f"原：{o}\n" for o in remaining))
    else:
        tail.unlink(missing_ok=True)
    progress.append(dict(slug=slug, title=title, annotated=count, paragraphs=len(originals),
                         translated_sentences=sum(len(split_sents(c["o"])) for c in chunks),
                         notes=sum(len(c["notes"]) for c in chunks),
                         next_paragraph=count + 1 if remaining else None,
                         next_text=remaining[0][:45] if remaining else None))
(BASE / "progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n")
for p in progress:
    print(f'{p["title"]} {p["annotated"]}/{p["paragraphs"]} 段')
