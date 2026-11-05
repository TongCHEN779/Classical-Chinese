"""Assemble the three Xuanzhenzi reading pages from the witness and original glosses."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/xuanzhenzi"
VOLUMES = (("碧虚", (3, 4, 5)), ("惊驽", (10, 11, 12, 13)),
           ("涛之灵", (18, 19, 20, 21, 22, 23, 24)))


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf8"))


def prepare():
    source, cleaned, omit = read("wikisource.json"), read("text.json"), read("omit.json")
    for i, (title, ids) in enumerate(VOLUMES, 1):
        slug = f"p{i:02}"
        annotations = read(f"{slug}-annotations.json")
        assert annotations["题解"].strip()
        assert set(annotations["段落"]) == set(map(str, ids)), slug
        lines = [f"# {title}", f"题解：{annotations['题解']}"]
        count = 0
        for j in ids:
            original = "".join(source["blocks"][j]["text"].split())
            for note in omit.get(str(j), "").split():
                assert original.count(note) == 1
                original = original.replace(note, "")
            assert original == cleaned[str(j)]
            item = annotations["段落"][str(j)]
            modern = item["译"]
            assert len(modern) == len(split_sents(original)), (slug, j)
            assert all(t.strip() and not any(c in t for c in "¦\r\n") for t in modern), (slug, j)
            lines.append(f"原：{original} || {'¦'.join(modern)}")
            lines.extend(f"注：{n}" for n in item.get("注", []))
            count += len(modern)
        path = ROOT / "src/xuanzhenzi" / slug / "001.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf8")
        print(title, count)


if __name__ == "__main__":
    prepare()
