"""由 sources/lunheng/chapters.json（维基文库《论衡》各卷正文，已去李善注）与 annotations/*.json（自撰题解、白话、注释）
生成 src/lunheng/*/01.txt。annotations/<slug>.json 为列表，与该卷 sections 一一对应：
[{"题解": "...", "段落": [{"译": ["每句白话"], "注": ["词语：解释"]}, ...]}, ...]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/lunheng"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def page_title(ch):
    names = [re.sub(r"篇第.+$", "", sec["title"]) for sec in ch["sections"]]
    return f'{ch["title"]}·{"、".join(names)}'


def prepare(only=None, strict=True):
    chapters = read(BASE / "chapters.json")
    report = []
    for ch in chapters:
        slug = ch["slug"]
        if only and slug not in only:
            continue
        path = BASE / "annotations" / f"{slug}.json"
        draft = read(path) if path.exists() else []
        assert len(draft) <= len(ch["sections"]), slug
        lines, total, done = [], 0, 0
        for i, sec in enumerate(ch["sections"]):
            item = (draft[i] or {}) if i < len(draft) else {}
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
                    assert len(gloss) == n and all(t and not any(c in t for c in "¦\r\n|") for t in gloss), (slug, i, j)
                    lines.append(f"原：{original} || {'¦'.join(gloss)}")
                    done += n
                else:
                    lines.append(f"原：{original}")
                lines.extend(f"注：{x.strip()}" for x in data.get("注", []))
        target = ROOT / "src/lunheng" / slug / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf8")
        report.append((slug, done, total))
    return report


def prepare_safe(only=None):
    """逐页生成；某页的注释稿有错只报错，不影响其他页（并行撰写期间使用）。"""
    report = []
    for ch in read(BASE / "chapters.json"):
        if only and ch["slug"] not in only:
            continue
        try:
            report += prepare({ch["slug"]})
        except AssertionError as e:
            print("ERROR", ch["slug"], e)
    return report


if __name__ == "__main__":
    rep = prepare_safe(set(sys.argv[1:]) or None)
    for slug, done, total in rep:
        print(slug, done, "/", total)
    print("合计", sum(d for _, d, _ in rep), "/", sum(t for _, _, t in rep))
