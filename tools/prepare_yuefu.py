"""由 sources/yuefu/chapters.json（维基文库《乐府诗集》各卷，按小节拆开）与 annotations/*.json（自撰题解、白话、注释）
生成 src/yuefu/*/01.txt。annotations/<slug>__<起始节>.json 为 {"start": a, "items": [...]}，items 与该卷第 a 节起的各节一一对应：
{"题解": "...", "段落": [{"译": ["每句白话"], "注": ["词语：解释"]}, ...]}
只有白话与题解齐全的卷才写入 src/，并记入 sources/yuefu/progress.json（build.py 只收录已完成的卷）。
  python3 tools/prepare_yuefu.py [卷slug …]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/yuefu"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def load_draft(slug, n):
    draft = [None] * n
    for path in sorted((BASE / "annotations").glob(f"{slug}__*.json")):
        data = read(path)
        start, items = data["start"], data["items"]
        assert start + len(items) <= n, (path.name, start, len(items), n)
        for k, it in enumerate(items):
            draft[start + k] = it
    return draft


def prepare_one(ch):
    slug = ch["slug"]
    draft = load_draft(slug, len(ch["sections"]))
    lines, total, done, guides = [], 0, 0, 0
    for i, sec in enumerate(ch["sections"]):
        item = draft[i] or {}
        lines.append(f"# {sec['title']}")
        if guide := item.get("题解", "").strip():
            lines.append(f"题解：{guide}")
            guides += 1
        paragraphs = item.get("段落", [])
        assert len(paragraphs) <= len(sec["paragraphs"]), (slug, i, len(paragraphs), len(sec["paragraphs"]))
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
            lines.extend(f"注：{x.strip()}" for x in data.get("注", []) if x.strip())
    complete = done == total and guides == len(ch["sections"])
    return lines, done, total, guides, complete


def prepare(only=None):
    chapters = read(BASE / "chapters.json")
    progress_path = BASE / "progress.json"
    complete = set(read(progress_path)["complete"]) if progress_path.exists() else set()
    report = []
    for ch in chapters:
        slug = ch["slug"]
        if only and slug not in only:
            continue
        try:
            lines, done, total, guides, ok = prepare_one(ch)
        except AssertionError as e:
            print("ERROR", slug, e)
            continue
        target = ROOT / "src/yuefu" / slug / "01.txt"
        if ok:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(lines) + "\n", encoding="utf8")
            complete.add(slug)
        else:
            complete.discard(slug)
            if target.exists():
                target.unlink()
        report.append((slug, done, total, guides, len(ch["sections"]), ok))
    order = [c["slug"] for c in chapters]
    progress_path.write_text(json.dumps({"complete": [s for s in order if s in complete]}, ensure_ascii=False) + "\n", encoding="utf8")
    return report


if __name__ == "__main__":
    rep = prepare(set(sys.argv[1:]) or None)
    for slug, done, total, guides, secs, ok in rep:
        if done or guides:
            print(slug, f"{done}/{total}句", f"题解{guides}/{secs}", "完成" if ok else "")
    print("合计", sum(r[1] for r in rep), "/", sum(r[2] for r in rep), "完成卷数", sum(r[5] for r in rep))
