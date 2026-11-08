"""由 sources/dongpozhilin/chapters.json（维基文库《东坡志林》序与五卷正文）与 annotations/ 下的自撰题解、白话、注释
生成 src/dongpozhilin/<slug>/01.txt。

annotations/<slug>__<起始节>.json：{"start": 起始节序号, "items": [{"题解": "...", "段落": [{"译": ["每句白话"], "注": ["词语：解释"]}, ...]}, ...]}
items 与该卷从 start 起的各节一一对应。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/dongpozhilin"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def load_draft(slug, n):
    """合并同卷各分片；返回长度为 n 的列表，缺的位置为 None。"""
    draft = [None] * n
    for f in sorted((BASE / "annotations").glob(f"{slug}__*.json")):
        d = read(f)
        for k, item in enumerate(d["items"]):
            assert d["start"] + k < n, (f.name, k)
            draft[d["start"] + k] = item
    return draft


def prepare(only=None):
    report = []
    for ch in read(BASE / "chapters.json"):
        slug = ch["slug"]
        if only and slug not in only:
            continue
        draft = load_draft(slug, len(ch["sections"]))
        lines, total, done = [], 0, 0
        for i, sec in enumerate(ch["sections"]):
            item = draft[i] or {}
            lines.append(f"# {sec['title']}")
            if guide := item.get("题解", "").strip():
                lines.append(f"题解：{guide}")
            paragraphs = item.get("段落", [])
            assert len(paragraphs) <= len(sec["paragraphs"]), (slug, i)
            for j, original in enumerate(sec["paragraphs"]):
                n = len(split_sents(original))
                total += n
                data = (paragraphs[j] or {}) if j < len(paragraphs) else {}
                gloss = [t.strip() for t in data.get("译", [])]
                if gloss:
                    assert len(gloss) == n and all(t and not any(c in t for c in "¦\r\n|") for t in gloss), (slug, i, j, n, len(gloss))
                    lines.append(f"原：{original} || {'¦'.join(gloss)}")
                    done += n
                else:
                    lines.append(f"原：{original}")
                lines.extend(f"注：{x.strip()}" for x in data.get("注", []))
        target = ROOT / "src/dongpozhilin" / slug / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf8")
        report.append((slug, done, total))
    return report


if __name__ == "__main__":
    rep = prepare(set(sys.argv[1:]) or None)
    for slug, done, total in rep:
        print(slug, done, "/", total)
    print("合计", sum(d for _, d, _ in rep), "/", sum(t for _, _, t in rep))
