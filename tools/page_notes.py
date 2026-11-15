#!/usr/bin/env python3
"""给 src/<书>/<页>/01.txt 这类“一行一段”的标注文本补题解与注释（韩非子、桃花扇用）。

注释稿：sources/<书>/annotations/<页>.json = {"题解": "…", "段落": [{"注": ["词语：解释", …]}, …]}
“段落”与该页以“原：”“诗：”开头的行一一对应；词语必须是该段原文（不含“||”后的白话）里的连续字串，且落在同一个“/”分行内。

  python3 tools/page_notes.py show  BOOK PAGE     列出该页各段（序号、字数、原文）
  python3 tools/page_notes.py check BOOK PAGE     核验注释稿（格式、段数、词语在原文里、密度）
  python3 tools/page_notes.py apply BOOK [PAGE…]  把注释稿写入 src（先去掉旧的“题解：”“注：”行，可重复运行）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARA = ("原：", "诗：")


def src_path(book, page):
    return ROOT / "src" / book / page / "01.txt"


def ann_path(book, page):
    return ROOT / "sources" / book / "annotations" / f"{page}.json"


def base_lines(path_or_text):
    text = path_or_text.read_text(encoding="utf8") if isinstance(path_or_text, Path) else path_or_text
    return [l for l in text.split("\n") if l and not l.startswith(("题解：", "注："))]


def para_text(line):
    """段落行的原文（去掉前缀和“||”后的白话）。"""
    return line[2:].split("||", 1)[0].strip()


def apply_lines(lines, ann):
    out, k = [], 0
    for l in lines:
        out.append(l)
        if l.startswith("# ") and ann.get("题解", "").strip():
            out.append("题解：" + ann["题解"].strip())
        elif l.startswith(PARA):
            if k < len(ann.get("段落", [])):
                out += ["注：" + n for n in (ann["段落"][k] or {}).get("注", [])]
            k += 1
    return out


def apply_page(book, page, lines=None):
    f = ann_path(book, page)
    if not f.exists():
        return False
    lines = lines if lines is not None else base_lines(src_path(book, page))
    ann = json.loads(f.read_text(encoding="utf8"))
    src_path(book, page).write_text("\n".join(apply_lines(lines, ann)) + "\n", encoding="utf8")
    return True


def paragraphs(book, page):
    return [l for l in base_lines(src_path(book, page)) if l.startswith(PARA)]


def check(book, page, dens=150):
    errs = []
    f = ann_path(book, page)
    if not f.exists():
        return ["没有注释稿"]
    ann = json.loads(f.read_text(encoding="utf8"))
    paras = paragraphs(book, page)
    if not ann.get("题解", "").strip():
        errs.append("缺题解")
    seg = ann.get("段落", [])
    if len(seg) != len(paras):
        return errs + [f"段落数 {len(seg)} ≠ {len(paras)}"]
    total = chars = 0
    for i, (line, item) in enumerate(zip(paras, seg)):
        text = para_text(line)
        chars += len(text.replace("/", ""))
        parts = text.split("/")
        seen = set()
        for n in (item or {}).get("注", []):
            total += 1
            w = n.split("：", 1)[0].strip() if "：" in n else ""
            if not w or "：" not in n:
                errs.append(f"段{i} 注格式应为“词语：解释”：{n[:20]}")
            elif not any(w in x for x in parts):
                errs.append(f"段{i} 词语不在本段原文（或跨“/”）：{w}")
            elif w in seen:
                errs.append(f"段{i} 词语重复：{w}")
            seen.add(w)
    if chars >= dens and total * dens < chars * 0.6:
        errs.append(f"注太少：{chars} 字仅 {total} 条")
    return errs


def main():
    cmd, book = sys.argv[1], sys.argv[2]
    if cmd == "show":
        for i, l in enumerate(paragraphs(book, sys.argv[3])):
            t = para_text(l)
            print(f"[{i}] ({len(t.replace('/', ''))}字) {t}")
    elif cmd == "check":
        e = check(book, sys.argv[3])
        print("OK" if not e else "\n".join(e[:30]))
        sys.exit(1 if e else 0)
    elif cmd == "apply":
        pages = sys.argv[3:] or sorted(p.name for p in (ROOT / "src" / book).iterdir() if ann_path(book, p.name).exists())
        n = sum(apply_page(book, p) for p in pages)
        print("写入", n, "页")


if __name__ == "__main__":
    main()
