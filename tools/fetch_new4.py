#!/usr/bin/env python3
"""缓存《贞观政要》《读通鉴论》《天工开物》《日知录》的维基文库原文，写入 sources/<slug>/chapters.json
（格式同 tools/fetch_texts.py，由 tools/prepare_texts.py 配合 annotations 生成 src/）。

  python3 tools/fetch_new4.py [slug ...]

- 贞观政要、读通鉴论、日知录：每卷一页，按页内标题（篇/条）分节；
- 日知录卷二十四、二十六、二十八无标题，卷二十四、二十六按“○条目”分节，卷二十八按每 4 段并节；
- 天工开物：自序一页，十八篇各一页，篇首引言与各子页（如“稻”“麦”）各为一节；
- 〈…〉小注、 wiki 的上标注记一律不收（同 fetch_texts）；条目标题前的“○●”装饰不进节名，正文不改。
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
from fetch_texts import items, build_sections, lead

CN = "零一二三四五六七八九十"


def num(n):
    if n <= 10:
        return CN[n]
    if n < 20:
        return "十" + CN[n - 10]
    return CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")


def seq_of(wiki):
    page = fetch(wiki, retries=8)
    soup = BeautifulSoup(page["text"], "html.parser")
    red = soup.select_one(".redirectMsg a")
    if red:
        wiki = unquote(red["href"])[6:]
        page = fetch(wiki, retries=8)
        soup = BeautifulSoup(page["text"], "html.parser")
    root = soup.select_one(".mw-parser-output")
    return wiki, list(items(root)), str(page["revid"])


def entry(slug, title, wiki, rev, secs):
    for sec in secs:      # 原页面漏出的 wiki 标记（如日知录卷二的“}}</ref>”）不属于正文
        sec["paragraphs"] = [p.replace("}}</ref>", "").replace("<ref>", "") for p in sec["paragraphs"]]
    return {"slug": slug, "title": title, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
            "revision": rev, "heads": [], "sections": secs}


def tidy(secs):
    for s in secs:
        s["title"] = re.sub(r"^[○●◎\s]+", "", s["title"]).strip() or s["title"]
        if s["path"] and re.fullmatch(r"[〇一二三四五六七八九十]+", s["title"]):     # 读通鉴论：只有序号的条，冠以所属帝王
            s["title"] = f"{s['path'][-1]}·{s['title']}"
    return secs


def by_circle(seq, page_title):
    """无标题页：以“○条目 …”开头的段落起一节，其后不带○的段落并入。"""
    secs, cur = [], None
    for l, t in seq:
        if l:
            continue
        if re.match(r"^[○●]", t) or cur is None:
            title = re.sub(r"^[○●\s]+", "", t)
            m = re.match(r"([^\s，。：；？！“‘「]{1,12})", title)
            cur = {"title": (m.group(1) if m else title[:8]), "level": 3, "path": [page_title], "author": "", "paragraphs": []}
            secs.append(cur)
        cur["paragraphs"].append(t)
    return secs


def zhenguan():
    wiki, seq, rev = seq_of("貞觀政要")
    paras, on = [], False
    for l, x in seq:
        if l:
            on = (x == "序")
        elif on:
            paras.append(x)
    out = [entry("x1", "序", wiki, rev, [{"title": "序", "level": 2, "path": [], "author": "", "paragraphs": paras}])]
    for n in range(1, 11):
        wiki, seq, rev = seq_of(f"貞觀政要/卷{n:02}")
        out.append(entry(f"j{n:02}", f"卷{num(n)}", wiki, rev, tidy(build_sections(seq, "headings", f"卷{num(n)}"))))
    return out


def dutongjian():
    out = []
    for n, t in enumerate(["一", "二", "三", "四"], 1):
        wiki, seq, rev = seq_of(f"讀通鑒論/敘論{t}")
        paras = [x for l, x in seq if l == 0]
        out.append(entry(f"x{n}", f"叙论{t}", wiki, rev,
                         [{"title": f"叙论{t}", "level": 2, "path": [], "author": "", "paragraphs": paras}]))
    for n in range(1, 31):
        wiki, seq, rev = seq_of(f"讀通鑒論/卷{n:02}")
        out.append(entry(f"j{n:02}", f"卷{num(n)}", wiki, rev, tidy(build_sections(seq, "headings", f"卷{num(n)}"))))
    return out


def rizhilu():
    wiki, seq, rev = seq_of("日知錄/自序")
    out = [entry("x1", "自序", wiki, rev, [{"title": "初刻日知录自序", "level": 2, "path": [], "author": "",
                                            "paragraphs": [x for l, x in seq if l == 0]}])]
    wiki, seq, rev = seq_of("日知錄序")
    out.append(entry("x2", "原序", wiki, rev, [{"title": "原序", "level": 2, "path": [], "author": "",
                                                "paragraphs": [x for l, x in seq if l == 0]}]))
    for n in range(1, 33):
        wiki, seq, rev = seq_of(f"日知錄/卷{n:02}")
        t = f"卷{num(n)}"
        if n in (24, 26):
            secs = by_circle([(l, x) for l, x in seq if not (l == 0 and re.fullmatch(r"卷.+", x))], t)
        elif n == 28:
            paras = [x for l, x in seq if l == 0 and not re.fullmatch(r"卷.+", x)]
            secs = [{"title": lead(paras[i]), "level": 3, "path": [t], "author": "", "paragraphs": paras[i:i + 4]}
                    for i in range(0, len(paras), 4)]
        else:
            secs = tidy(build_sections(seq, "headings", t))
            secs = [s for s in secs if not re.fullmatch(r"卷.+", s["title"])]
        out.append(entry(f"j{n:02}", t, wiki, rev, secs))
    return out


def tiangong():
    page = fetch("天工開物", retries=8)
    soup = BeautifulSoup(page["text"], "html.parser")
    root = soup.select_one(".mw-parser-output")
    links = []
    for a in root.select("ul a"):
        href = unquote(a.get("href", ""))
        if href.startswith("/wiki/天工開物/"):
            links.append((a.get_text().strip(), href[6:]))
    chap = re.compile(r"第[一二三四五六七八九十]+$")
    groups, cur = [], None
    for text, wt in links:
        if text == "自序":
            groups.append(("自序", wt, []))
            cur = None
        elif chap.search(text):
            cur = (text, wt, [])
            groups.append(cur)
        elif cur is not None:
            cur[2].append((text, wt))
    out = []
    for i, (title, wt, subs) in enumerate(groups):
        slug = "x1" if title == "自序" else f"p{i:02}"
        wiki, seq, rev = seq_of(wt)
        paras = [x for l, x in seq if l == 0]
        if title == "自序":
            out.append(entry(slug, "自序", wiki, rev, [{"title": "自序", "level": 2, "path": [], "author": "", "paragraphs": paras}]))
            continue
        secs = []
        if paras:
            secs.append({"title": title, "level": 2, "path": [], "author": "", "paragraphs": paras})
        for st, swt in subs:
            w2, s2, _ = seq_of(swt)
            sp = [x for l, x in s2 if l == 0]
            name = re.sub(r"^附[：:]", "附·", st)
            secs.append({"title": name, "level": 3, "path": [title], "author": "", "paragraphs": sp})
            print("  ", title, name, len(sp), sum(len(x) for x in sp), flush=True)
        out.append(entry(slug, title, wiki, rev, secs))
    return out


BOOKS = {"zhenguanzhengyao": zhenguan, "dutongjianlun": dutongjian, "rizhilu": rizhilu, "tiangongkaiwu": tiangong}


def main():
    want = set(sys.argv[1:]) or set(BOOKS)
    for slug, fn in BOOKS.items():
        if slug not in want:
            continue
        out = fn()
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print("==", slug)
        for c in out:
            print("  ", c["slug"], c["title"], len(c["sections"]), sum(len(s["paragraphs"]) for s in c["sections"]),
                  sum(len(p) for s in c["sections"] for p in s["paragraphs"]))


if __name__ == "__main__":
    main()
