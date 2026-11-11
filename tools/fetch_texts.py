#!/usr/bin/env python3
"""缓存维基文库的一批短篇典籍原文，写入 sources/<slug>/chapters.json（格式同《东坡志林》）。

  python3 tools/fetch_texts.py [slug ...]

页面配置见 BOOKS：每页指定维基文库标题与分节方式——
  headings：按页内标题分节（含正文的最内层标题为一节）；
  single：整页一节；
  chunk=N：无标题的页，每 N 个段落并为一节，节名取首段开头几个字。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch

CN = "零一二三四五六七八九"

BOOKS = {
    "shipin": {"title": "詩品", "pages": [
        ("xu", "序", "詩品", "single"), ("j1", "卷上", "詩品/卷上", "headings"),
        ("j2", "卷中", "詩品/卷中", "headings"), ("j3", "卷下", "詩品/卷下", "headings")]},
    "weilu": {"title": "圍爐夜話", "pages": [("p01", "围炉夜话", "圍爐夜話", "chunk=8")]},
    "caigentan": {"title": "菜根譚", "pages": [
        ("p01", "序", "菜根譚", "headings:序"),
        ("p02", "明刻本·前集", "菜根譚", "h2:前集@明刻本《菜根谭》:chunk=10"),
        ("p03", "明刻本·后集", "菜根譚", "h2:后集@明刻本《菜根谭》:chunk=10"),
        ("p04", "清刻本·修身", "菜根譚", "h2:修身@清刻本《菜根谭》:chunk=10"),
        ("p05", "清刻本·应酬", "菜根譚", "h2:应酬@清刻本《菜根谭》:chunk=10"),
        ("p06", "清刻本·评议", "菜根譚", "h2:评议@清刻本《菜根谭》:chunk=10"),
        ("p07", "清刻本·闲适", "菜根譚", "h2:闲适@清刻本《菜根谭》:chunk=10"),
        ("p08", "清刻本·概论", "菜根譚", "h2:概论@清刻本《菜根谭》:chunk=10")]},
    "fusheng": {"title": "浮生六記", "pages": [
        ("j1", "卷一 闺房记乐", "浮生六記/卷一 閨房記樂", "chunk=6"), ("j2", "卷二 闲情记趣", "浮生六記/卷二 閑情記趣", "chunk=6"),
        ("j3", "卷三 坎坷记愁", "浮生六記/卷三 坎坷記愁", "chunk=6"), ("j4", "卷四 浪游记快", "浮生六記/卷四 浪遊記快", "chunk=6"),
        ("j5", "卷五 中山记历（伪续）", "浮生六記/卷五 中山記歷", "chunk=6"), ("j6", "卷六 养生记道（伪续）", "浮生六記/卷六 養生記道", "chunk=6")]},
    "zengguang": {"title": "增廣昔時賢文", "pages": [("p01", "上集", "增廣昔時賢文", "h2:上集:chunk=20"), ("p02", "下集", "增廣昔時賢文", "h2:下集:chunk=20")]},
    "yanshi": {"title": "顏氏家訓", "pages": [(f"j{n}", f"卷第{CN[n]}", f"顏氏家訓/卷第{n}", "headings") for n in range(1, 8)]},
    "sunzi": {"title": "孫子兵法", "pages": [("p01", "孙子兵法", "孫子兵法", "headings")]},
    "sunbin": {"title": "孫臏兵法", "pages": [("p01", "孙膑兵法", "孫臏兵法", "headings")]},
    "fansheng": {"title": "西湖老人繁勝錄", "pages": [("p01", "西湖老人繁胜录", "西湖老人繁勝錄", "chunk=6")]},
    "yinwenzi": {"title": "尹文子", "pages": [
        ("xu", "序", "尹文子/序", "single"), ("p01", "大道上", "尹文子/大道上", "chunk=5"),
        ("p02", "大道下", "尹文子/大道下", "chunk=5"), ("p03", "佚文", "尹文子/佚文", "single")]},
    "shenbuhai": {"title": "申子", "pages": [("p01", "申子", "申子", "headings")]},
    "shendao": {"title": "慎子", "pages": [("p01", "慎子", "慎子", "headings")]},
    "shiliuguochunqiu": {"title": "十六國春秋", "pages": [
        ("p01", "卷一·前赵录", "十六國春秋/卷01", "headings"),
        ("p02", "卷二·后赵录", "十六國春秋/卷02", "headings"),
        ("p03", "卷三·前燕录", "十六國春秋/卷03", "headings"),
        ("p04", "卷四·前秦录", "十六國春秋/卷04", "headings"),
        ("p05", "卷五·后秦录", "十六國春秋/卷05", "headings"),
        ("p06", "卷六·蜀录", "十六國春秋/卷06", "headings"),
        ("p07", "卷七·前凉录", "十六國春秋/卷07", "headings"),
        ("p08", "卷八·西凉录", "十六國春秋/卷08", "headings"),
        ("p09", "卷九·北凉录", "十六國春秋/卷09", "headings"),
        ("p10", "卷十·后凉录", "十六國春秋/卷10", "headings"),
        ("p11", "卷十一·后燕录", "十六國春秋/卷11", "headings"),
        ("p12", "卷十二·南凉录", "十六國春秋/卷12", "headings"),
        ("p13", "卷十三·南燕录", "十六國春秋/卷13", "headings"),
        ("p14", "卷十四·西秦录", "十六國春秋/卷14", "headings"),
        ("p15", "卷十五·北燕录", "十六國春秋/卷15", "headings"),
        ("p16", "卷十六·夏录", "十六國春秋/卷16", "headings")]},
}


def clean(node):
    for x in node.select("span.variant-tooltip, sup.reference, style, link, ol.references, table, .noprint"):
        x.decompose()
    t = re.sub(r"\[\d+\]", "", node.get_text("", strip=False))
    t = re.sub(r"〈[^〈〉]*〉", "", t)           # 校勘小注（如慎子的钱熙祚校语）不是正文
    return re.sub(r"\s+", " ", t).replace("　", "").replace("﻿", "").strip()


def items(root):
    """依次产出 (标题级别, 文本) 或 (0, 段落)；列表项与诗行也算段落。"""
    for x in root.select("table, .licenseContainer, ol.references, style, meta, link, #headerContainer, .hatnote, ul#toc"):
        x.decompose()
    for el in root.find_all(["div", "p", "ol", "ul", "dl"], recursive=False):
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


def lead(t, n=10):
    m = re.match(r"[^，。；：！？、]{1,%d}" % n, t)
    return (m.group(0) if m else t[:n]).strip() + "…"


def build_sections(seq, mode, page_title):
    # mode: single | headings | chunk=N | h2:NAME[@PARENT][:chunk=N] | headings:NAME
    if mode == "single":
        return [{"title": page_title, "level": 2, "path": [], "author": "", "paragraphs": [t for l, t in seq if l == 0]}]
    m = re.fullmatch(r"chunk=(\d+)", mode)
    if m:
        paras = [t for l, t in seq if l == 0]
        n = int(m.group(1))
        return [{"title": lead(paras[i]), "level": 3, "path": [page_title], "author": "", "paragraphs": paras[i:i + n]}
                for i in range(0, len(paras), n)]
    m = re.fullmatch(r"h2:([^@:]+)(?:@([^:]+))?(?::chunk=(\d+))?", mode)
    if m:
        name, parent, n = m.group(1), m.group(2), int(m.group(3) or 0)
        cur_parent, on, paras = "", False, []
        for l, t in seq:
            if l == 1:
                cur_parent = t
            elif l == 2:
                on = (t == name) and (not parent or cur_parent == parent)
            elif l == 0 and on:
                paras.append(t)
        paras = [p for p in paras if not re.fullmatch(r"\(\d+\)", p)]      # “(222)”之类的条数标注
        if not n:
            return [{"title": name, "level": 2, "path": [], "author": "", "paragraphs": paras}]
        return [{"title": lead(paras[i]), "level": 3, "path": [page_title], "author": "", "paragraphs": paras[i:i + n]}
                for i in range(0, len(paras), n)]
    only = mode.split(":", 1)[1] if mode.startswith("headings:") else None
    secs, cur, trail, skip = [], None, [], only is not None
    for l, t in seq:
        if l:
            if only is not None and l == 1:
                skip = (t != only)
            if only is not None and l == 1:
                trail = []
                cur = None
                continue
            while trail and trail[-1][0] >= l:
                trail.pop()
            trail.append((l, t))
            cur = None if skip else {"title": t, "level": l, "path": [x for _, x in trail[:-1]], "author": "", "paragraphs": []}
            if cur:
                secs.append(cur)
        elif cur is not None:
            cur["paragraphs"].append(t)
    if only is not None:
        return [s for s in secs if s["paragraphs"]]
    # 页首无标题的正文并入第一节之前的“序”
    return [s for s in secs if s["paragraphs"]]


def main():
    want = set(sys.argv[1:])
    for slug, cfg in BOOKS.items():
        if want and slug not in want:
            continue
        out, cache = [], {}
        for pslug, ptitle, wiki, mode in cfg["pages"]:
            if wiki not in cache:
                page = fetch(wiki)
                root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
                cache[wiki] = (list(items(root)), str(page["revid"]))
            seq, rev = cache[wiki]
            secs = build_sections(seq, mode, ptitle)
            out.append({"slug": pslug, "title": ptitle, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
                        "revision": rev, "heads": [], "sections": secs})
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print("==", slug, d.name)
        for c in out:
            print("  ", c["slug"], c["title"], len(c["sections"]), sum(len(s["paragraphs"]) for s in c["sections"]),
                  sum(len(p) for s in c["sections"] for p in s["paragraphs"]))


if __name__ == "__main__":
    main()
