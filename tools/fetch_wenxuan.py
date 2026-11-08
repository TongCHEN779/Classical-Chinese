#!/usr/bin/env python3
"""缓存维基文库《昭明文选》（胡克家重刊尤袤刻李善注本）六十卷正文：去掉李善注、文选考异、脚注标号，写入 sources/wenxuan/。

  python3 tools/fetch_wenxuan.py
"""
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

BASE = ROOT / "sources/wenxuan"
CN = "零一二三四五六七八九"


def cn(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n - 10] if n > 10 else "")
    t, u = divmod(n, 10)
    return CN[t] + "十" + (CN[u] if u else "")


def fetch(title, retries=5):
    for attempt in range(retries):
        try:
            time.sleep(1.2)
            return json.loads(get(API, {"action": "parse", "page": title, "prop": "text|revid", "variant": "zh-hans",
                                        "disableeditsection": 1, "format": "json", "formatversion": 2}))["parse"]
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3 * 2 ** attempt)


def clean(node):
    for x in node.select("small, sup.reference, style, ol.references, table, .noprint, .mw-heading + dl dd > .noprint"):
        x.decompose()
    t = re.sub(r"\[\d+\]", "", node.get_text("", strip=False))
    t = re.sub(r"〈[^〈〉]*〉", "", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_juan(n):
    page = fetch(f"昭明文選/卷{n}")
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    for x in root.select("div.prose, div.poem"):
        x.unwrap()
    for x in root.select("table, .licenseContainer, ol.references, ul, style, meta, link"):
        x.decompose()
    trail, sections, cur, heads = [], [], None, []   # trail: [(level, title)] 当前标题路径
    for el in root.find_all(["div", "p", "dl"], recursive=False):
        cls = el.get("class") or []
        if "mw-heading" in cls:
            lvl = int(el.find(re.compile("h[1-6]")).name[1])
            while trail and trail[-1][0] >= lvl:
                trail.pop()
            trail.append((lvl, clean(el)))
            cur = {"title": trail[-1][1], "level": lvl, "path": [t for _, t in trail[:-1]], "author": "", "paragraphs": []}
            sections.append(cur)
            continue
        if el.name == "p":
            blocks = [el]
        else:
            if el.find(string=re.compile("主页面")):
                continue
            blocks = el.find_all("dd")
        for b in blocks:
            t = clean(b)
            if not t or t == "文选考异":
                continue
            if cur is None:
                heads.append(t)
            elif not cur["paragraphs"] and not cur["author"] and len(t) <= 5 and not re.search("[，。！？；：]", t):
                cur["author"] = t   # 紧随标题的短行是作者
            else:
                cur["paragraphs"].append(t)
    # 无正文的标题只作分类路径；正文段落留在最近的有正文标题下
    real = [s for s in sections if s["paragraphs"]]
    for s in real:
        s["path"] = [t for t in s["path"] if t]
    return {"slug": f"j{n:02}", "title": f"卷{cn(n)}", "url": "https://zh.wikisource.org/zh-hans/" + quote(f"昭明文選/卷{n}"),
            "revision": str(page["revid"]), "heads": heads, "sections": real}


XU_TITLES = ("文选序", "唐李崇贤上文选注表", "宋刻原序", "重刻宋淳熙本文选序", "《文选考异》序")


def parse_xu():
    """卷首序文：《文选序》、李善《上文选注表》、尤袤《宋刻原序》、胡克家《重刻宋淳熙本文选序》与《文选考异》序。"""
    page = fetch("昭明文選/序")
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    for x in root.select("table, .licenseContainer, style, meta, link"):
        x.decompose()
    sections, cur = [], None
    for el in root.find_all(["div", "p"], recursive=False):
        if "mw-heading" in (el.get("class") or []):
            title = clean(el)
            cur = {"title": title, "level": 2, "path": [], "author": "", "paragraphs": []} if title in XU_TITLES else None
            if cur:
                sections.append(cur)
        elif el.name == "p" and cur is not None:
            t = clean(el)
            if t:
                cur["paragraphs"].append(t)
    return {"slug": "xu", "title": "序", "url": "https://zh.wikisource.org/zh-hans/" + quote("昭明文選/序"),
            "revision": str(page["revid"]), "heads": [], "sections": sections}


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    toc = fetch("昭明文選")
    root = BeautifulSoup(toc["text"], "html.parser").select_one(".mw-parser-output")
    for x in root.select("style, table.sistersitebox"):
        x.decompose()
    lines = [l.strip() for l in root.get_text("\n").splitlines() if l.strip()]
    (BASE / "toc.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    (BASE / "intro.json").write_text(json.dumps({"revision": str(toc["revid"]), "url": "https://zh.wikisource.org/zh-hans/" + quote("昭明文選"),
        "text": lines[lines.index(next(l for l in lines if l.startswith("《文选》")))] if any(l.startswith("《文选》") for l in lines) else ""},
        ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    juan = [parse_xu()]
    for n in range(1, 61):
        j = parse_juan(n)
        juan.append(j)
        print(j["slug"], len(j["sections"]), sum(len(s["paragraphs"]) for s in j["sections"]), flush=True)
    (BASE / "chapters.json").write_text(json.dumps(juan, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
