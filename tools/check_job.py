#!/usr/bin/env python3
"""核验一个注译作业文件：python3 tools/check_job.py BOOK 页slug 起始节 结束节
检查：JSON 可读；items 数 = 节数；每节有题解；段落数与原文一致；每段译句数 = 切句数且无空句、无“¦|”及换行；
注格式“词语：解释”，词语须在该段原文里；每 MINCH 字原文至少 1 条注（日知录等密注书）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import NOTES_ONLY, sent_units


def check(book, slug, a, b, minch=220):
    ch = next(c for c in json.loads((ROOT / "sources" / book / "chapters.json").read_text(encoding="utf8")) if c["slug"] == slug)
    f = ROOT / "sources" / book / "annotations" / f"{slug}__{a}.json"
    d = json.loads(f.read_text(encoding="utf8"))
    errs = []
    if d.get("start") != a:
        errs.append(f"start 应为 {a}")
    secs = ch["sections"][a:b]
    items = d.get("items", [])
    if len(items) != len(secs):
        return [f"items 数 {len(items)} ≠ 节数 {len(secs)}"]
    for k, (sec, it) in enumerate(zip(secs, items)):
        tag = f"节{a + k}《{sec['title']}》"
        if not it.get("题解", "").strip():
            errs.append(f"{tag} 缺题解")
        ps = it.get("段落", [])
        if len(ps) != len(sec["paragraphs"]):
            errs.append(f"{tag} 段落数 {len(ps)} ≠ {len(sec['paragraphs'])}")
            continue
        chars = sum(len(p) for p in sec["paragraphs"])
        nn = 0
        for j, (orig, p) in enumerate(zip(sec["paragraphs"], ps)):
            n = len(sent_units(orig))
            g = [t.strip() for t in p.get("译", [])]
            if book in NOTES_ONLY:       # 白话/半白话原文只写注释，译必须为空
                if g:
                    errs.append(f"{tag} 段{j} 本书不写白话，译应为空数组")
            elif len(g) != n:
                errs.append(f"{tag} 段{j} 译句数 {len(g)} ≠ 切句数 {n}：{' | '.join(sent_units(orig))[:80]}")
            elif not all(g) or any(c in t for t in g for c in "¦|\r\n"):
                errs.append(f"{tag} 段{j} 译含空句或非法字符")
            for x in p.get("注", []):
                nn += 1
                w = x.split("：", 1)[0].strip() if "：" in x else ""
                if not w or "：" not in x:
                    errs.append(f"{tag} 段{j} 注格式应为“词语：解释”：{x[:20]}")
                elif w not in orig:
                    errs.append(f"{tag} 段{j} 注词语不在本段原文：{w}")
        if chars >= minch and nn * minch < chars * 0.5:
            errs.append(f"{tag} 注太少：{chars} 字仅 {nn} 条")
    return errs


if __name__ == "__main__":
    book, slug, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    e = check(book, slug, a, b)
    if e:
        print("\n".join(e[:40]))
        sys.exit(1)
    print("OK")
