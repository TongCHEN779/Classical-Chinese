"""Combine the Dengxizi source paragraphs with the original annotations."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/dengxizi"
PAGES = (("p01", "无厚"), ("p02", "转辞"))


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf8"))


def prepare():
    for slug, title in PAGES:
        original = [b["text"] for b in read(f"{slug}.json")["blocks"]]
        data = read(f"{slug}-annotations.json")
        items = data["段落"]
        assert items.keys() == {str(i) for i in range(len(original))}, slug
        assert data["题解"].strip(), slug
        lines = [f"# {title}", f"题解：{data['题解']}"]
        for i, paragraph in enumerate(original):
            item = items[str(i)]
            modern = item["译"]
            assert len(modern) == len(split_sents(paragraph)), (slug, i)
            assert all(t.strip() and not any(c in t for c in "¦\r\n") for t in modern), (slug, i)
            lines.append(f"原：{paragraph} || {'¦'.join(modern)}")
            lines.extend(f"注：{note}" for note in item.get("注", []))
        path = ROOT / "src/dengxizi" / slug / "001.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf8")


if __name__ == "__main__":
    prepare()
