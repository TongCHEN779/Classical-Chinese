#!/usr/bin/env python3
"""缓存维基文库的几部较长的笔记游记（扬州画舫录、陶庵梦忆、帝京景物略、都城纪胜、梦粱录、徐霞客游记），
写入 sources/<slug>/chapters.json（格式同 tools/fetch_texts.py）。

  python3 tools/fetch_books2.py [slug ...]

分节：每个标题（及其下正文）是一个单元；单元超过 G 字时按段落贪心切成若干节（不切断段落），
节名为“标题·首段开头”；游记按日期标题的相邻小单元合并成一节（节名“月·初一日至初五日”）。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch
from fetch_texts import items, lead

CN = "零一二三四五六七八九十"


def num(n):
    return CN[n] if n <= 10 else "十" + (CN[n - 10] if n > 10 and n < 20 else "") if n < 20 else CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")


BOOKS = {
    "huafanglu": {"wiki": "揚州畫舫錄", "g": 1800, "pages": (
        [("x1", "袁枚序", "揚州畫舫錄/袁枚序"), ("x2", "阮元序", "揚州畫舫錄/阮元序"), ("x3", "自序", "揚州畫舫錄/自序")]
        + [(f"j{n:02}", f"卷{num(n)}", f"揚州畫舫錄/{n:02}") for n in range(1, 19)])},
    "taoan": {"wiki": "陶庵夢憶", "g": 3000, "pages": (
        [("x1", "梦忆序", "陶庵夢憶/夢憶序"), ("x2", "陶庵梦忆序", "陶庵夢憶/陶庵夢憶序")]
        + [(f"j{n}", f"卷{num(n)}", f"陶庵夢憶/卷{n:02}") for n in range(1, 9)]
        + [("j9", "补", "陶庵夢憶/陶庵夢憶補"), ("x3", "伍跋", "陶庵夢憶/伍跋")])},
    "dijing": {"wiki": "帝京景物略", "g": 2500, "poem": True, "pages": (
        [("x0", "序与略例", "帝京景物略/0")] + [(f"j{n}", f"卷{num(n)}", f"帝京景物略/{n}") for n in range(1, 9)])},
    "ducheng": {"wiki": "都城紀勝", "g": 2500, "pages": [("p01", "都城纪胜", "都城紀勝")]},
    "mengliang": {"wiki": "夢粱錄", "g": 2500, "pages": (
        [("x1", "序", "夢粱錄/序")] + [(f"j{n:02}", f"卷{num(n)}", f"夢粱錄/卷{n:02}") for n in range(1, 21)])},
    "xuxiake": {"wiki": "徐霞客遊記", "g": 1800, "merge": True, "pages": "AUTO"},
}


def units(seq, poem=False):
    """seq 为 items() 的输出，返回 [(标题, 上级标题, 段落列表)]。"""
    out, trail, cur = [], [], None
    for lvl, t in seq:
        if lvl:
            if poem and "【" in t and cur is not None:
                cur[2].append(t)        # 诗题并入正文，作为该诗的首行
                continue
            while trail and trail[-1][0] >= lvl:
                trail.pop()
            parent = trail[-1][1] if trail else ""
            trail.append((lvl, t))
            cur = (t, parent, [])
            out.append(cur)
        else:
            if cur is None:
                cur = ("", "", [])
                out.append(cur)
            cur[2].append(t)
    return [u for u in out if u[2]]


def sections(us, page_title, g, merge):
    if not us:
        return []
    secs = []
    # 1. 切分超长单元
    pieces = []
    for title, parent, paras in us:
        groups, cur, size = [], [], 0
        for p in paras:
            if cur and size + len(p) > g:
                groups.append(cur)
                cur, size = [], 0
            cur.append(p)
            size += len(p)
        if cur:
            groups.append(cur)
        for k, grp in enumerate(groups):
            name = title or page_title
            if len(groups) > 1 or not title:
                name = (title + "·" if title else "") + lead(grp[0])
            pieces.append({"title": name, "parent": parent, "head": title, "paragraphs": grp})
    # 2. 游记：合并相邻的小单元
    if merge:
        merged = []
        for p in pieces:
            size = sum(len(x) for x in p["paragraphs"])
            if (merged and merged[-1]["size"] + size <= g and merged[-1]["parent"] == p["parent"]
                    and p["head"] and merged[-1]["head"] and "·" not in p["title"] and "·" not in merged[-1]["title"]):
                m = merged[-1]
                m["paragraphs"] += p["paragraphs"]
                m["size"] += size
                m["last"] = p["head"]
            else:
                merged.append({**p, "size": size, "first": p["head"], "last": p["head"]})
        pieces = []
        for m in merged:
            if m.get("first") and m["first"] != m["last"]:
                name = f'{m["first"]}至{m["last"]}'
            else:
                name = m["title"]
            if m["parent"] and m["parent"] not in name and m.get("head") and "·" not in name:
                name = f'{m["parent"]}·{name}'
            pieces.append({"title": name, "paragraphs": m["paragraphs"]})
    return [{"title": p["title"], "level": 3, "path": [page_title], "author": "", "paragraphs": p["paragraphs"]} for p in pieces]


def main():
    want = set(sys.argv[1:])
    for slug, cfg in BOOKS.items():
        if want and slug not in want:
            continue
        pages = cfg["pages"]
        if pages == "AUTO":
            main_page = fetch(cfg["wiki"])
            soup = BeautifulSoup(main_page["text"], "html.parser")
            pages = []
            for i, a in enumerate(soup.select(".mw-parser-output ul li a"), 1):
                href = unquote(a.get("href", ""))
                if cfg["wiki"] in href and "/wiki/" in href:
                    wt = href.split("/wiki/", 1)[1].replace("_", " ")
                    pages.append((f"p{len(pages) + 1:02}", a.get_text().strip(), wt))
        out = []
        for pslug, ptitle, wiki in pages:
            try:
                page = fetch(wiki)
            except Exception as e:            # 页面不存在（目录里的红链）等
                print("SKIP", slug, pslug, ptitle, wiki, type(e).__name__, flush=True)
                continue
            root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
            seq = list(items(root))
            secs = sections(units(seq, cfg.get("poem", False)), ptitle, cfg["g"], cfg.get("merge", False))
            out.append({"slug": pslug, "title": ptitle, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
                        "revision": str(page["revid"]), "heads": [], "sections": secs})
            print(slug, pslug, ptitle, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
