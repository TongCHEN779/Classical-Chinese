#!/usr/bin/env python3
"""把四库本《文献通考》缺卷的标点稿（sources/wenxiantongkao/punct/<卷>.json，原文见 sk_pages.json）并入
sources/wenxiantongkao/chapters.json，页按卷号插入（新页 slug 从 p164 起，旧页 slug 不动）。
小标题：标点稿里无句末标点的短行（长度≤30、不含。？！；）另起一节；其前的正文归首节（节名取考名）。
小注〈…〉若在节末仍未闭合，补一个〉，免得后面整节变成小字灰体。
  python3 tools/merge_wxtk_sk.py        然后  python3 tools/prepare_orig.py wenxiantongkao
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_orig import cn2int, num

PUNCT = "。，、；：？！“”‘’《》（）…—·　 "
END = "。？！”’"


def strip(t):
    return "".join(c for c in t if c not in PUNCT)


def is_heading(p):
    s = strip(p)
    body = p[:-1] if p.endswith("〉") else p
    return len(s) <= 30 and not any(c in p for c in "。？！；") and not body.endswith(tuple("，、：”’"))


def balance(paras):
    depth, fixed = 0, 0
    for c in "".join(paras):
        if c == "〈":
            depth += 1
        elif c == "〉" and depth:
            depth -= 1
    if depth:
        paras[-1] += "〉" * depth
        fixed = depth
    return fixed


def main():
    pages = json.loads((ROOT / "sources/wenxiantongkao/sk_pages.json").read_text(encoding="utf8"))
    cpath = ROOT / "sources/wenxiantongkao/chapters.json"
    chapters = json.loads(cpath.read_text(encoding="utf8"))
    chapters = [c for c in chapters if not c.get("sk")]      # 重跑时先去掉上次并入的
    new, fixed = [], 0
    for k in sorted(pages, key=int):
        f = ROOT / "sources/wenxiantongkao/punct" / f"{k}.json"
        if not f.exists():
            continue
        paras = [re.sub(r"</?span[^>]*>", "", x) for x in json.loads(f.read_text(encoding="utf8"))]    # 个别段带维基页内链接标记
        title = pages[k]["title"]
        kao = title.split("·", 1)[1]
        secs, cur = [], None
        for p in paras:
            if is_heading(p):
                cur = {"title": p, "level": 2, "path": [], "author": "", "paragraphs": []}
                secs.append(cur)
            else:
                if cur is None:
                    cur = {"title": kao, "level": 2, "path": [], "author": "", "paragraphs": []}
                    secs.append(cur)
                cur["paragraphs"].append(p)
        secs = [s for s in secs if s["paragraphs"]]
        for s in secs:
            fixed += balance(s["paragraphs"])
        new.append({"slug": "", "title": title, "head": "", "sk": True, "juan": int(k),
                    "url": "https://zh.wikisource.org/zh-hans/" + quote(f"文獻通考 (四庫全書本)/卷{int(k):03d}"),
                    "revision": "sk", "heads": [], "sections": secs})

    def juan_of(c):
        m = re.match(r"卷([一二三四五六七八九十百零〇]+)", c["title"])
        return cn2int(m.group(1)) if m else (0 if c["slug"] == "p001" else 10 ** 6)

    order = {int(k): i for i, k in enumerate(sorted(pages, key=int))}      # slug 按全部缺卷的序号定，增量并入时不变
    for c in new:
        c["slug"] = f"p{164 + order[c['juan']]:03}"
    allc = sorted(chapters + new, key=lambda c: (c.get("juan") or juan_of(c)))
    for c in allc:
        c.pop("juan", None)
    cpath.write_text(json.dumps(allc, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("并入", len(new), "卷；补〉", fixed, "处；共", len(allc), "页")


if __name__ == "__main__":
    main()
