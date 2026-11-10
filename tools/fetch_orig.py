#!/usr/bin/env python3
"""缓存维基文库的四部大书（水经注、后汉书、汉书、太平广记），只取原文，写入 sources/<slug>/chapters.json
（格式同 tools/fetch_books2.py）。

  python3 tools/fetch_orig.py [slug ...]

页面标题取自各页页眉；节名取页内已有标题，无标题的页整页一节。
底本的小注（页面上以小字显示、前后有隐形〈〉的）保留〈…〉，由 build.py 渲成小字灰色。
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch
from fetch_books2 import units, sections

CN = "零一二三四五六七八九十"


def clean(node):
    for x in node.select("span.variant-tooltip, sup.reference, style, link, ol.references, table, .noprint"):
        x.decompose()
    t = re.sub(r"\[\d+\]", "", node.get_text("", strip=False))
    return re.sub(r"\s+", " ", t).replace("　", "").replace("﻿", "").strip()


def items(root):
    """依次产出 (标题级别, 文本)；级别 0 是段落（列表项、dd 也算）。"""
    for x in root.select("table, .licenseContainer, ol.references, style, meta, link, #headerContainer, .hatnote, ul#toc, .ws-header"):
        x.decompose()
    box = root.select_one("div.text") or root
    for el in box.find_all(["div", "p", "ol", "ul", "dl"], recursive=False):
        cls = el.get("class") or []
        if "mw-heading" in cls:
            h = el.find(re.compile("h[1-6]"))
            yield int(h.name[1]), clean(h)
        elif el.name == "p":
            t = clean(el)
            if t:
                yield 0, t
        elif el.name in ("ol", "ul", "dl") or "poem" in cls or "prose" in cls:
            for li in el.find_all(["li", "dd", "p"]):
                if li.find(["li", "dd"]):
                    continue
                t = clean(li)
                if t:
                    yield 0, t
        elif el.name == "div":
            for li in el.find_all(["li", "p", "dd"]):
                t = clean(li)
                if t:
                    yield 0, t


def header_title(soup):
    """页眉里的书名/卷名那一格。"""
    for td in soup.select("table.ws-header td, #headerContainer td"):
        t = td.get_text(" ", strip=True)
        if re.match(r"^(后汉书|汉书|水经注|太平广记)\s", t) or re.match(r"^卷第.+\u3000", t):
            return t
    return ""


def page_of(wiki):
    p = fetch(wiki, retries=8)
    soup = BeautifulSoup(p["text"], "html.parser")
    redir = soup.select_one(".redirectMsg a")
    frag = ""
    if redir:                               # 重定向页：取目标（可能带 #上/#下 之类的页内锚点）
        wiki = unquote(redir["href"])[6:]
        if "#" in wiki:
            wiki, frag = wiki.split("#", 1)
        p = fetch(wiki, retries=8)
        soup = BeautifulSoup(p["text"], "html.parser")
    return wiki, p, soup, frag


def cut(seq, frag):
    """合页（如汉书卷五十七上、下同在一页）：按 上/中/下 标题截取。"""
    top = min((l for l, _ in seq if l), default=0)
    out, on = [], False
    for l, t in seq:
        if l == top and t in ("上", "中", "下"):
            on = (t == frag)
            continue
        if on:
            out.append((l, t))
    return out


def book_pages(book):
    """返回 [(slug, 页面标题, 维基标题)]，以及分组 [(组名, 起始slug)]。"""
    if book == "shuijingzhu":
        pages = [("x1", "原序", "水經注/原序")] + [(f"j{n:02}", f"卷{num(n)}", f"水經注/{n:02}") for n in range(1, 41)]
        return pages
    if book == "taipingguangji":
        return [(f"j{n:03}", f"卷{num(n)}", f"太平廣記/卷第{n:03}") for n in range(1, 501)]
    wiki = WIKI[book]
    main = fetch(wiki)
    soup = BeautifulSoup(main["text"], "html.parser")
    pages = []
    for a in soup.select(".mw-parser-output a"):
        href = unquote(a.get("href", ""))
        if "#" in href or not href.startswith("/wiki/" + wiki + "/") or href.count("/") != 3:
            continue
        wt = href[6:]
        if any(wt == p[2] for p in pages):
            continue
        pages.append((None, a.get_text().strip(), wt))
    if book in ("houhanshu", "hanshu"):
        return pages
    pages.sort(key=lambda p: page_key(p[2]))
    return pages


def cn2int(s):
    d = {c: i for i, c in enumerate("零一二三四五六七八九")}
    d["〇"] = 0
    if re.fullmatch(r"\d+", s):
        return int(s)
    n, cur = 0, 0
    for ch in s:
        if ch in d:
            cur = d[ch]
        elif ch == "十":
            n += (cur or 1) * 10
            cur = 0
        elif ch == "百":
            n += (cur or 1) * 100
            cur = 0
    return n + cur


def page_key(wt):
    """卷N（上中下）按数字序；序、表、引一类排前，跋、附录、补遗排后。"""
    tail = wt.split("/", 1)[1]
    m = re.match(r"卷(?:第)?([0-9一二三四五六七八九十百零〇]+)(.*)$", tail)
    if m:
        return (1, cn2int(m.group(1)), "上中下".find(m.group(2)[:1]) if m.group(2)[:1] in "上中下" else 0, tail)
    if re.search(r"序|引|叙|敘|表|例", tail):
        m = re.search(r"([一二三四五六七八九十]+)$", tail)
        return (0, cn2int(m.group(1)) if m else 0, 0, tail)
    return (2, 0, 0, tail)


WIKI = {"houhanshu": "後漢書", "hanshu": "漢書", "sanguozhi": "三國志", "jinshu": "晉書", "nanshi": "南史", "beishi": "北史",
        "jiutangshu": "舊唐書", "xintangshu": "新唐書", "mingshi": "明史", "suishu": "隋書", "songshi": "宋史", "songshu": "宋書",
        "nanqishu": "南齊書", "liangshu": "梁書", "chenshu": "陳書", "weishu": "魏書", "beiqishu": "北齊書", "zhoushu": "周書",
        "liaoshi": "遼史", "jinshi": "金史", "yuanshi": "元史", "jiuwudaishi": "舊五代史", "xinwudaishi": "新五代史",
        "tongdian": "通典", "wenxiantongkao": "文獻通考", "ershierzhaji": "廿二史劄記"}


def num(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n - 10] if n > 10 else "")
    if n < 100:
        return CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")
    h, r = divmod(n, 100)
    out = CN[h] + "百"
    if r == 0:
        return out
    if r < 10:
        return out + "零" + CN[r]
    if r < 20:
        return out + "一十" + (CN[r - 10] if r > 10 else "")
    return out + num(r)


def main():
    want = set(sys.argv[1:]) or {"shuijingzhu", "houhanshu", "hanshu", "taipingguangji"}
    for book in ["shuijingzhu", "taipingguangji"] + list(WIKI):
        if book not in want:
            continue
        cache = ROOT / "sources" / book / "chapters.json"
        done = {}
        if cache.exists():
            done = {c["slug"]: c for c in json.loads(cache.read_text(encoding="utf8"))}
        out = []
        pages = book_pages(book)
        for i, (pslug, ptitle, wiki) in enumerate(pages, 1):
            pslug = pslug or f"p{i:03}"
            if pslug in done:
                out.append(done[pslug])
                continue
            try:
                wiki, page, soup, frag = page_of(wiki)
            except Exception as e:
                print("SKIP", book, pslug, ptitle, wiki, type(e).__name__, flush=True)
                continue
            root = soup.select_one(".mw-parser-output")
            head = header_title(soup)
            seq = list(items(root))
            if frag:
                seq = cut(seq, frag)
            secs = sections(units(seq), ptitle, 10 ** 7, False)
            out.append({"slug": pslug, "title": ptitle, "head": head, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
                        "revision": str(page["revid"]), "heads": [], "sections": secs})
            print(book, pslug, ptitle, "|", head, "|", len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
            if i % 20 == 0:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
