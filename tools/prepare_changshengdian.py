"""由 sources/changshengdian/chapters.json（维基文库《长生殿》五十出）与 annotations/<slug>.json 的自撰题解、注释
生成 src/changshengdian/<slug>/01.txt（原文＋题解＋基础注释，无白话）。

annotations/<slug>.json：{"题解": "...", "段落": [{"注": ["词语：解释"]}, ...]}，“段落”与该出各块（chapters.json blocks）一一对应。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "sources/changshengdian"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def prepare(only=None):
    report = []
    for ch in read(BASE / "chapters.json"):
        slug = ch["slug"]
        if only and slug not in only:
            continue
        path = BASE / "annotations" / f"{slug}.json"
        draft = read(path) if path.exists() else {}
        paras = draft.get("段落", [])
        assert len(paras) in (0, len(ch["blocks"])), (slug, len(paras), len(ch["blocks"]))
        lines = [f"# {ch['title']}"]
        if guide := draft.get("题解", "").strip():
            lines.append(f"题解：{guide}")
        notes = 0
        for j, b in enumerate(ch["blocks"]):
            lines.append(f"{b['kind']}：{b['text']}")
            for x in (paras[j].get("注", []) if paras else []):
                term = x.split("：", 1)[0].strip()
                assert "：" in x and term, (slug, j, x)
                lines.append(f"注：{x.strip()}")
                notes += 1
        target = ROOT / "src/changshengdian" / slug / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf8")
        report.append((slug, bool(draft), notes))
    return report


if __name__ == "__main__":
    rep = prepare(set(sys.argv[1:]) or None)
    print("已写", sum(1 for _, d, _ in rep if d), "/", len(rep), "出；注释", sum(n for _, _, n in rep), "条")
