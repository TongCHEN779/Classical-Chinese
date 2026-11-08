"""Assemble Xinlun from clean source sections and independently written glosses."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/xinlun"
OMIT = {"p11": {15, 17}, "p15": {12}}  # Separate editorial parallels from the Hanshu.


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf8"))


def supplement_sections(slug):
    """序/附录的节与段落：xu 只有一节（无小标题），appendix 按 h2 分节。"""
    secs = []
    for b in read(f"{slug}-wikisource.json")["blocks"]:
        text = "".join(b["text"].splitlines()).strip()
        if b["type"].startswith("h"):
            secs.append({"title": text, "paragraphs": []})
        else:
            if not secs:
                secs.append({"title": None, "paragraphs": []})
            secs[-1]["paragraphs"].append(text)
    return secs


def emit(slug, head, sections, report):
    path = BASE / "annotations" / f"{slug}.json"
    draft = read(f"annotations/{slug}.json") if path.exists() else []
    assert len(draft) <= len(sections), slug
    lines, total, done = list(head), 0, 0
    for i, sec in enumerate(sections):
        if sec["title"]:
            lines.append(f"# {sec['title']}")
        item = (draft[i] or {}) if i < len(draft) else {}
        if guide := item.get("题解", "").strip():
            lines.append(f"题解：{guide}")
        paragraphs = item.get("段落", [])
        assert len(paragraphs) <= len(sec["paragraphs"]), (slug, i)
        for j, original in enumerate(sec["paragraphs"]):
            if j in OMIT.get(slug, ()):
                continue
            n = len(split_sents(original))
            total += n
            data = (paragraphs[j] or {}) if j < len(paragraphs) else {}
            gloss = [t.strip() for t in data.get("译", [])]
            if gloss:
                assert len(gloss) == n and all(t.strip() and not any(c in t for c in "¦\r\n") for t in gloss), (slug, i, j)
                lines.append(f"原：{original} || {'¦'.join(gloss)}")
                done += n
            else:
                lines.append(f"原：{original}")
            lines.extend(f"注：{note.strip()}" for note in data.get("注", []))
    target = ROOT / "src/xinlun" / slug / "01.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf8")
    report.append((slug, done, total))


def prepare():
    report = []
    emit("xu", ["# 朱谦之自序"], supplement_sections("xu"), report)
    emit("appendix", ["# 附录"], supplement_sections("appendix"), report)
    for p in read("catalog.json"):
        slug = p["slug"]
        emit(slug, [], read(slug + ".json")["sections"], report)
    return report


if __name__ == "__main__":
    for slug, done, total in prepare():
        print(slug, done, "/", total)
