#!/usr/bin/env python3
"""Validate Shangshu source drafts and rebuild their completion manifest offline."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build

SOURCES = ROOT / "sources/shangshu"
APPARATUS = re.compile(r"（[^（）]*）|〈[^〈〉]*〉|［[^［］]*］|｛[^｛｝]*｝|\{[^{}]*\}|\([^()]*\)")


def clean(text):
    return APPARATUS.sub("", text.replace("\n", ""))


def selected_blocks(slug, blocks):
    # These pages append parallel transmitted/excavated texts, not part of
    # the transmitted chapter in this edition of the collection.
    end = {"p12": 5, "p34": 4}.get(slug, len(blocks))
    return [i for i, b in enumerate(blocks[:end]) if b["type"] == "p"]


def normalize_pairs(o, t):
    """Remove apparatus, merging glosses when apparatus punctuation divided a sentence."""
    old = build.split_sents(o)
    ts = t.split("¦")
    assert "".join(old) == o and len(ts) == len(old) and all(x.strip() for x in ts)
    if clean(o) == o:
        return o, t
    discard = set(i for m in APPARATUS.finditer(o) for i in range(*m.span()))
    parts = build.split_sents(clean(o))
    pos = 0
    runs = []
    for s, tr in zip(old, ts):
        keep = "".join(ch for i, ch in enumerate(s, pos) if i not in discard)
        pos += len(s)
        if keep:
            runs.append((keep, tr))
    modern = []
    i = 0
    for part in parts:
        pair_text, gloss = "", []
        while len(pair_text) < len(part) and i < len(runs):
            a, b = runs[i]
            pair_text += a
            gloss.append(b)
            i += 1
        assert pair_text == part, (o, part, pair_text)
        modern.append("".join(gloss))
    assert i == len(runs)
    return clean(o), "¦".join(modern)


def main():
    catalog = json.loads((SOURCES / "catalog.json").read_text(encoding="utf8"))
    progress_path = SOURCES / "progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf8"))
    pages, pending, rewrites = [], [], []
    for item in [{"slug": "shuxu", "title": "书序"}] + catalog:
        slug = item["slug"]
        path = ROOT / "src/shangshu" / slug / "01.txt"
        if not path.exists():
            pending.append(item["title"])
            continue
        source = json.loads((SOURCES / "wikisource" / (slug + ".json")).read_text(encoding="utf8"))
        inds = selected_blocks(slug, source["blocks"])
        witness = clean("".join(source["blocks"][i]["text"] for i in inds))
        text = path.read_text(encoding="utf8")
        entries = build.parse_poems([path])
        chunks = [c for s in entries for c in s["chunks"]]
        assert chunks and all(s["intro"] for s in entries), slug
        assert clean("".join(c["o"] for c in chunks)) == witness, (slug, "正文不全或混有非正文")
        assert any(c["notes"] for c in chunks), (slug, "未写注释")
        output, pairs = [], 0
        for line in text.splitlines():
            if line.startswith("原："):
                o, t = (v.strip() for v in line[2:].split("||", 1))
                try:
                    o, t = normalize_pairs(o, t)
                except AssertionError as e:
                    raise ValueError((slug, o, e.args)) from e
                assert [a for a, _ in build.split_pairs(o, t)] == build.split_sents(o), (slug, o)
                pairs += len(t.split("¦"))
                line = f"原：{o} || {t}"
            output.append(line)
        updated = "\n".join(output) + "\n"
        if updated != text:
            rewrites.append((path, updated))
        title = item["title"].split("，原文见", 1)[0].replace("（伪）", "（伪古文）")
        pages.append(dict(slug=slug, title=title, status="complete", selected_blocks=inds,
                          normalization="editorial_apparatus", sections=len(entries), pairs=pairs,
                          notes=sum(len(c["notes"]) for c in chunks),
                          original_sha256=hashlib.sha256(witness.encode()).hexdigest(),
                          source={k: source[k] for k in ("url", "revision")}))
    for path, text in rewrites:
        path.write_text(text, encoding="utf8")
    progress.update(status="in_progress" if pending else "complete",
                    scope="虞、夏、商、周四书传世58篇及卷首书序；不混入清华简或同页对读材料",
                    next=pending[0] if pending else None, pages=pages)
    progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(len(pages), "complete;", len(pending), "pending:", "、".join(pending))


if __name__ == "__main__":
    main()
