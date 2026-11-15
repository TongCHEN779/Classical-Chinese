#!/usr/bin/env python3
"""缓存维基文库《随园诗话》（十六卷）与《随园诗话补遗》（十卷）、《瓯北诗话》（小引与十二卷）：
写入 sources/suiyuanshihua/chapters.json、sources/oubeishihua/chapters.json，页首提要并入 sources/wiki_intros.json（如有）。

  python3 tools/fetch_shihua.py [CACHE_DIR]     CACHE_DIR 里若已有 <标题>.json（API 原始返回，/ 换成 _）则不再联网

《随园诗话》：每条（页内编号标题“一、二…”）一段或数段；每条（页内编号标题）为一节，节名为条号。
《瓯北诗话》：整书一页，卷（二级标题）为页，诗家小标题为节；原站为每行二十字左右的硬换行，已合并成段；过长的节按段落切开，节名“小标题·首段开头”。
"""
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
G = 2200
CN = "零一二三四五六七八九十"


def cn(n):
    if n <= 10:
        return CN[n]
    if n < 20:
        return "十" + CN[n - 10] if n > 10 else "十"
    t, u = divmod(n, 10)
    return CN[t] + "十" + (CN[u] if u else "")


def raw_page(title, cache):
    f = Path(cache) / (title.replace("/", "_") + ".json") if cache else None
    if f and f.exists():
        return json.loads(f.read_text(encoding="utf8"))["parse"]
    url = ("https://zh.wikisource.org/w/api.php?format=json&formatversion=2&action=parse&prop=text%7Crevid&variant=zh-hans"
           "&disableeditsection=1&page=" + urllib.parse.quote(title))
    for k in range(8):
        out = subprocess.run(["curl", "-s", "-m", "200", "-w", "\n%{http_code}", url], capture_output=True, text=True).stdout
        body, _, code = out.rpartition("\n")
        if code == "200" and body.startswith("{"):
            time.sleep(3)
            return json.loads(body)["parse"]
        time.sleep(30 * (k + 1))
    raise RuntimeError(title)


def root_of(page):
    r = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    for x in r.select("table, .noprint, style, .licenseContainer, sup.reference, ol.references"):
        x.decompose()
    return r


def para_text(el):
    t = el.get_text("").replace("\n", "").replace("　", "")
    return re.sub(r"\s+", "", t)


def lead(p, n=8):
    p = re.sub(r"[〔〕\s]", "", p)
    return p[:n] + ("…" if len(p) > n else "")


def group(paras, g=G):
    out, cur, size = [], [], 0
    for p in paras:
        if cur and size + len(p) > g:
            out.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += len(p)
    if cur:
        out.append(cur)
    return out


def suiyuan(cache):
    pages = [(f"j{n:02d}", f"卷{cn(n)}", f"隨園詩話/{n:02d}") for n in range(1, 17)] + \
            [(f"b{n:02d}", f"补遗卷{cn(n)}", f"隨園詩話補遺/{n:02d}") for n in range(1, 11)]
    out = []
    for slug, title, wiki in pages:
        page = raw_page(wiki, cache)
        items, cur = [], None          # [(条号, [段])]
        for el in root_of(page).children:
            if not getattr(el, "name", None):
                continue
            cls = el.get("class") or []
            if "mw-heading" in cls:
                cur = [el.get_text(strip=True), []]
                items.append(cur)
            elif el.name == "p":
                t = para_text(el)
                if t and cur is not None:
                    cur[1].append(t)
        secs = [{"title": num, "level": 3, "path": [title], "author": "", "paragraphs": ps} for num, ps in items if ps]      # 每条一节，节名即条号
        out.append({"slug": slug, "title": title, "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(wiki),
                    "revision": str(page["revid"]), "heads": [], "sections": secs})
        print("随园", slug, title, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
    d = ROOT / "sources/suiyuanshihua"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


def oubei(cache):
    page = raw_page("甌北詩話", cache)
    units, cur_page, head = [], None, None      # 页：[(小标题, [段])]
    pages = []
    for el in root_of(page).children:
        if not getattr(el, "name", None):
            continue
        cls = el.get("class") or []
        if "mw-heading" in cls:
            h = el.find(re.compile("h[1-6]"))
            name = h.get_text(strip=True)
            if h.name == "h2":
                cur_page = {"title": name, "units": []}
                pages.append(cur_page)
                head = None
            else:
                head = [name, []]
                cur_page["units"].append(head)
        elif el.name == "p" and cur_page is not None:
            t = para_text(el)
            if not t:
                continue
            if head is None:
                head = [cur_page["title"], []]
                cur_page["units"].append(head)
            head[1].append(t)
    out = []
    for n, pg in enumerate(pages):
        slug = "x1" if pg["title"] == "小引" else f"j{n:02d}"
        secs = []
        for h, ps in pg["units"]:
            gs = group(ps)
            for g in gs:
                title = h if len(gs) == 1 else f"{h}·{lead(g[0])}"
                secs.append({"title": title, "level": 3, "path": [pg["title"]], "author": "", "paragraphs": g})
        out.append({"slug": slug, "title": pg["title"], "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote("甌北詩話"),
                    "revision": str(page["revid"]), "heads": [], "sections": secs})
        print("瓯北", slug, pg["title"], len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
    d = ROOT / "sources/oubeishihua"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    cache = sys.argv[1] if len(sys.argv) > 1 else None
    oubei(cache)
    suiyuan(cache)
