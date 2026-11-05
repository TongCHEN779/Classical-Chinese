"""Assemble the reading files from the Dadailiji witnesses and original glosses."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/dadailiji"


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def extract(slug):
    raw = read(BASE / f"{slug}.json")
    blocks = ["".join(re.sub(r"〈[^〈〉]*〉", "", b["text"]).split()) for b in raw["blocks"]]
    if slug == "p06":
        selection = read(BASE / "xia-selection.json")
        assert len(blocks) == len(selection)
        blocks = ["".join(sentences[i] if isinstance(i, int) else i for i in picks)
                  for b, picks in zip(blocks, selection) if (sentences := split_sents(b))]
    return [t for t in blocks if t]


def prepare():
    for p in read(BASE / "index.json")["pages"]:
        slug, title = p["slug"], p["title"]
        originals = read(BASE / "text" / f"{slug}.json")
        assert originals == extract(slug), slug
        draft = BASE / "annotations" / f"{slug}.json"
        data = read(draft) if draft.exists() else {}
        items = data.get("段落", {})
        assert items.keys() <= {str(i) for i in range(len(originals))}, slug
        lines = [f"# {title}"]
        if data.get("题解"):
            lines.append(f"题解：{data['题解']}")
        total = 0
        for i, original in enumerate(originals):
            item = items.get(str(i), {})
            translations = item.get("译", [])
            text = f"原：{original}"
            if translations:
                assert len(translations) == len(split_sents(original)), (slug, i)
                assert all(t.strip() and not any(c in t for c in "¦\r\n") for t in translations), (slug, i)
                text += " || " + "¦".join(translations)
                total += len(translations)
            lines.append(text)
            lines.extend(f"注：{note}" for note in item.get("注", []))
        path = ROOT / "src/dadailiji" / slug / "001.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf8")
        print(slug, total, "/", sum(len(split_sents(t)) for t in originals))


if __name__ == "__main__":
    prepare()
