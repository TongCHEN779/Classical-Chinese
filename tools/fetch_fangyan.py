#!/usr/bin/env python3
"""缓存维基文库《方言》（扬雄，郭璞注）：序、刻序、十三卷、跋及书名页提要，写入 sources/fangyan/。"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from catalog_zizhitongjian import API, get

BASE = ROOT / "sources/fangyan"
JUAN = "一二三四五六七八九十十一十二十三"
PAGES = [("xu", "郭璞序", "方言序"), ("kexu", "李孟传刻方言序", "刻方言序")]
for i, n in enumerate(["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"], 1):
    PAGES.append((f"p{i:02}", f"卷{n}", f"卷{n}"))
PAGES.append(("ba", "朱质跋李刻方言", "跋李刻方言"))


def parse(title):
    time.sleep(1.2)
    j = json.loads(get(API, {"action": "parse", "page": title, "prop": "text|revid", "variant": "zh-hans", "redirects": 1,
                             "disableeditsection": 1, "format": "json", "formatversion": 2}))["parse"]
    doc = BeautifulSoup(j["text"], "html.parser")
    paras = ["".join(p.get_text().splitlines()).strip() for p in doc.select(".mw-parser-output > p")]
    # 去掉维基文库编者的校勘说明段（形如“(1. 关 : 原作……。)”），它不是《方言》正文
    return str(j["revid"]), [p for p in paras if p and not re.match(r"^\(\d+\.", p)]


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    chapters = []
    for slug, title, wiki in PAGES:
        rev, paras = parse("方言/" + wiki)
        chapters.append({"slug": slug, "title": title, "url": "https://zh.wikisource.org/zh-hans/" + quote("方言/" + wiki),
                         "revision": rev, "paragraphs": paras})
        print(slug, title, rev, len(paras))
    (BASE / "chapters.json").write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    time.sleep(1.2)
    j = json.loads(get(API, {"action": "parse", "page": "方言", "prop": "text|revid", "variant": "zh-hans",
                             "disableeditsection": 1, "format": "json", "formatversion": 2}))["parse"]
    box = BeautifulSoup(j["text"], "html.parser").select_one("#headerContainer")
    for x in box.select("style"):
        x.decompose()
    lines = [l.strip() for l in box.get_text("\n").splitlines() if l.strip()]
    rev, paras = str(j["revid"]), [l for l in lines if l.startswith("旧本题") or len(l) > 80]
    (BASE / "intro.json").write_text(json.dumps({"text": "\n".join(paras), "revision": rev,
        "url": "https://zh.wikisource.org/zh-hans/" + quote("方言")}, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("intro", rev, len(paras), sum(map(len, paras)))


if __name__ == "__main__":
    main()
