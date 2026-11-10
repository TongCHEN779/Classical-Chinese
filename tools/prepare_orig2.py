#!/usr/bin/env python3
"""读通鉴论、日知录：只录原文（暂无白话与注释）。由 tools/fetch_new4.py 缓存的 sources/<slug>/chapters.json
生成 src/<slug>/<页>/01.txt 与 sources/<slug>/pages.json（页表与分组，组名用维基文库目录页上的已有标题）。
  python3 tools/prepare_orig2.py [slug ...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIG2_BOOKS = []      # 读通鉴论已改走 prepare_texts（注译），分组表仍由本脚本的 GROUPS 生成：python3 tools/prepare_orig2.py dutongjianlun

# 组名取自维基文库目录页；键为“卷号区间”
GROUPS = {
    "rizhilu": [(1, 7, "论经义"), (8, 12, "论政事"), (13, 13, "论世风"), (14, 15, "论礼制"), (16, 17, "论科举"),
                (18, 21, "论艺文"), (22, 24, "杂论名义"), (25, 25, "论古事真妄"), (26, 26, "论史法"), (27, 27, "论注书"),
                (28, 28, "论杂事"), (29, 29, "论兵及外国事"), (30, 30, "论天象术数"), (31, 31, "论地理"), (32, 32, "杂考证")],
    "dutongjianlun": [(1, 1, "秦"), (2, 5, "汉"), (6, 9, "后汉"), (10, 10, "三国"), (11, 14, "晋"), (15, 15, "宋"),
                      (16, 16, "齐"), (17, 17, "梁"), (18, 18, "陈"), (19, 19, "隋"), (20, 27, "唐"), (28, 30, "五代")],
}
FRONT = {"dutongjianlun": "叙论"}


def group(book, slug):
    if slug.startswith("x"):
        return FRONT.get(book)
    n = int(slug[1:])
    return next(g for a, b, g in GROUPS[book] if a <= n <= b)


def build(book):
    chapters = json.loads((ROOT / "sources" / book / "chapters.json").read_text(encoding="utf8"))
    pages = []
    for ch in chapters:
        d = ROOT / "src" / book / ch["slug"]
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        for s in ch["sections"]:
            lines.append("# " + s["title"])
            lines += ["原：" + p for p in s["paragraphs"]]
            lines.append("")
        (d / "01.txt").write_text("\n".join(lines), encoding="utf8")
        pages.append([ch["slug"], ch["title"], group(book, ch["slug"])])
    (ROOT / "sources" / book / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(book, len(pages), "页", sum(len(p) for c in chapters for s in c["sections"] for p in s["paragraphs"]), "字")


if __name__ == "__main__":
    for b in sys.argv[1:] or ORIG2_BOOKS:
        build(b)
