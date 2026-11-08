"""由 chapters.json（维基文库原文，含郭璞〈夹注〉）与 annotations/*.json（自撰题解、白话、注释）生成 src/fangyan/*/01.txt。

卷一至卷四底本带郭璞〈夹注〉：正文去掉夹注，夹注原样分条移入注释（“词：郭璞注“……””）；
序、刻序、跋里的〈…〉是原编者小注，保留在正文中。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/fangyan"
NOTE = re.compile(r"〈([^〈〉]*)〉")
JUAN = re.compile(r"^p\d\d$")


def anchor(before):
    """夹注紧跟在被注词之后：取其前面最后一个分句里“谓之/曰”后的词，否则取分句末几字。"""
    clause = re.split(r"[，。；、：]", before)[-1] if before and before[-1] not in "，。；、：" else ""
    if not clause:
        parts = [x for x in re.split(r"[，。；、：]", before) if x]
        clause = parts[-1] if parts else ""
    m = re.search(r"(?:谓之|曰|呼为|为|言|语|谓)([^，、。；：谓曰]{1,6})$", clause)
    word = m.group(1) if m else clause
    return word[-6:] if len(word) > 6 else word


def split_guo(text):
    """返回（去掉夹注的正文, [(词, 夹注)]）。"""
    notes, out, pos = [], "", 0
    for m in NOTE.finditer(text):
        out += text[pos:m.start()]
        notes.append((anchor(out), m.group(1).strip()))
        pos = m.end()
    out += text[pos:]
    assert "〈" not in out and "〉" not in out, text[:40]
    return out, notes


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def prepare():
    chapters = read(BASE / "chapters.json")
    report = []
    for ch in chapters:
        slug, title = ch["slug"], ch["title"]
        path = BASE / "annotations" / f"{slug}.json"
        draft = read(path) if path.exists() else {}
        paragraphs = draft.get("段落", [])
        assert len(paragraphs) <= len(ch["paragraphs"]), slug
        guo = JUAN.match(slug)
        lines, total, done = [f"# {title}"], 0, 0
        if guide := draft.get("题解", "").strip():
            lines.append(f"题解：{guide}")
        for j, raw in enumerate(ch["paragraphs"]):
            original, notes = split_guo(raw) if guo else (raw, [])
            n = len(split_sents(original))
            total += n
            data = (paragraphs[j] or {}) if j < len(paragraphs) else {}
            gloss = [t.strip() for t in data.get("译", [])]
            if gloss:
                assert len(gloss) == n and all(t and not any(c in t for c in "¦\r\n|") for t in gloss), (slug, j)
                lines.append(f"原：{original} || {'¦'.join(gloss)}")
                done += n
            else:
                lines.append(f"原：{original}")
            lines.extend(f"注：{w}：郭璞注“{n_}”" if w else f"注：郭璞注“{n_}”" for w, n_ in notes)
            lines.extend(f"注：{x.strip()}" for x in data.get("注", []))
        target = ROOT / "src/fangyan" / slug / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf8")
        report.append((slug, done, total))
    return report


if __name__ == "__main__":
    for slug, done, total in prepare():
        print(slug, done, "/", total)
