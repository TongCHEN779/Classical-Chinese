#!/usr/bin/env python3
"""维基文库缺的几部，改取中国哲学书电子化计划（ctext）：玉娇梨（全部二十回）、新编五代史平话的周史平话卷上、卷下。

  python3 tools/fetch_ctext_extra.py
写入 sources/yujiaoli/chapters.json；周史平话两卷并入 sources/wudaishipinghua/chapters.json（插在“跋”之前）。
ctext 是未经校对的电子本，间隔 7 秒抓取，不绕过验证码。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_ctext_books as f

ROOT = f.ROOT


def entry(slug, title, ch, paras):
    return {"slug": slug, "title": title, "head": "", "url": f"https://ctext.org/wiki.pl?if=gb&chapter={ch}", "revision": "ctext", "heads": [],
            "sections": [{"title": title, "level": 3, "path": [], "author": "", "paragraphs": paras}]}


def page(ch):
    h = f.get(f"https://ctext.org/wiki.pl?if=gb&chapter={ch}")
    return [f.T2S.convert(t) for k, t in f.rows(h) if k == "P"]


def main():
    f.BOOKS["yujiaoli"] = ("玉娇梨", 763355)
    idx, _ = f.index_of("yujiaoli")
    out = []
    for i, (ch, label) in enumerate(idx, 1):
        title = re.sub(r"\s+Chapter\s+\d+:.*$", "", f.T2S.convert(label)).strip()
        title = re.sub(r"^(第.+?回)", r"\1 ", title)
        paras = page(ch)
        print("yujiaoli", i, title, len(paras), sum(map(len, paras)), flush=True)
        if paras:
            out.append(entry(f"p{i:03d}", title, ch, paras))
    d = ROOT / "sources/yujiaoli"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    P = ROOT / "sources/wudaishipinghua/chapters.json"
    cat = json.loads(P.read_text(encoding="utf8"))
    if not any("周史" in c["title"] for c in cat):
        extra = []
        for ch, title in (("201043", "周史平话卷上"), ("384985", "周史平话卷下")):
            paras = page(ch)
            print("zhou", title, len(paras), sum(map(len, paras)), flush=True)
            extra.append(entry("", title, ch, paras))
        cat = cat[:-1] + extra + cat[-1:]
        for n, c in enumerate(cat, 1):
            c["slug"] = f"p{n:03d}"
        P.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
