#!/usr/bin/env python3
"""把 sk_raw.json（四库本《文献通考》缺卷的原文行）整理成无标点的分节稿 sources/wenxiantongkao/sk_pages.json：
{卷号: {"title": "卷八十三·郊社考十六", "paragraphs": [每行一段…]}}
页头三行（钦定四库全书／文献通考卷N／作者行）、页尾重复行与“<史部…>”图片说明丢弃；其后第一行是考名，作页题。
标点由 sources/wenxiantongkao/punct/<卷>.json 提供（见 tools/brief_punct_wxtk.md、tools/check_punct_wxtk.py）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_orig import num

HEAD_MAX = 14


def build():
    raw = json.loads((ROOT / "sources/wenxiantongkao/sk_raw.json").read_text(encoding="utf8"))
    out = {}
    for k, lines in raw.items():
        n = int(k)
        i = 0
        while i < len(lines) and (lines[i].startswith("钦定四库全书") or lines[i].replace(" ", "").startswith("文献通考卷")
                                   or re.search(r"马\s*端\s*临", lines[i])):
            i += 1
        body = [ln for ln in lines[i:] if not ln.startswith("<史部")
                and not re.fullmatch(r"文献通考卷[一二三四五六七八九十百零]+[上下]?", ln.replace(" ", ""))]
        if not body:
            continue
        # 第一行是考名（页题），其余每行一段；标点稿完成后，无句末标点的短行才视作小标题另起一节
        out[k] = {"title": f"卷{num(n)}·{body[0]}", "paragraphs": body[1:]}
    return out


if __name__ == "__main__":
    d = build()
    (ROOT / "sources/wenxiantongkao/sk_pages.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(len(d), "卷", sum(len(p) for v in d.values() for p in v["paragraphs"]), "字")
