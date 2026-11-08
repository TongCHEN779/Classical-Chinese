#!/usr/bin/env python3
"""缓存维基文库《论衡》（王充）八十五篇正文（招致篇今缺），按三十卷编组，写入 sources/lunheng/chapters.json。"""
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

BASE = ROOT / "sources/lunheng"
CN = "零一二三四五六七八九"


def cn(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n - 10] if n > 10 else "")
    t, u = divmod(n, 10)
    return CN[t] + "十" + (CN[u] if u else "")


def fetch(title):
    for attempt in range(5):
        try:
            time.sleep(1.2)
            return json.loads(get(API, {"action": "parse", "page": title, "prop": "text|revid", "variant": "zh-hans",
                                        "disableeditsection": 1, "format": "json", "formatversion": 2}))["parse"]
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3 * 2 ** attempt)


def paragraphs(page):
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    for x in root.select("table, .licenseContainer, style, ol.references, sup.reference, small"):
        x.decompose()
    out = []
    for p in root.find_all("p", recursive=False):
        t = re.sub(r"\[\d+\]", "", re.sub(r"\s+", " ", p.get_text())).strip()
        t = re.sub(r"w:([^\s:：，。！？；、“”（）]+):\s*\1", r"\1", t)   # 维基站际链接残留“w:某某: 某某”
        t = re.sub(r"w:(?=[\u4e00-\u9fff])", "", t)
        if t:
            out.append(t)
    return out


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    toc = fetch("論衡")
    root = BeautifulSoup(toc["text"], "html.parser").select_one(".mw-parser-output")
    lines = [l.strip() for l in root.get_text("\n").splitlines() if l.strip()]
    juan, cur = [], None
    merged = []
    for l in lines:        # 生僻字（如“𧬘时篇”的𧬘）在页面里单独成行，并回下一行
        if merged and len(merged[-1]) == 1 and l.startswith("时篇第"):
            merged[-1] += l
        else:
            merged.append(l)
    lines = merged
    for l in lines:
        m = re.fullmatch(r"论衡卷第([一二三四五六七八九十]+)", l)
        if m:
            cur = {"label": m.group(1), "titles": []}
            juan.append(cur)
        elif cur is not None and re.fullmatch(r".+篇第[一二三四五六七八九十]+", l):
            cur["titles"].append(l)
    assert len(juan) == 30 and sum(len(j["titles"]) for j in juan) == 85, (len(juan), sum(len(j["titles"]) for j in juan))
    chapters, n = [], 0
    for k, j in enumerate(juan, 1):
        secs = []
        for t in j["titles"]:
            n += 1
            page = fetch(f"論衡/{n:02}")
            secs.append({"title": t, "level": 2, "path": [], "author": "王充", "url": "https://zh.wikisource.org/zh-hans/" + quote(f"論衡/{n:02}"),
                         "revision": str(page["revid"]), "paragraphs": paragraphs(page)})
            print(n, t, len(secs[-1]["paragraphs"]), flush=True)
        chapters.append({"slug": f"j{k:02}", "title": f"卷{cn(k)}", "revision": str(toc["revid"]), "sections": secs})
    (BASE / "chapters.json").write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
