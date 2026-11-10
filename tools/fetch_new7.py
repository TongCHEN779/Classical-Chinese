#!/usr/bin/env python3
"""缓存《性命圭旨》《沧浪诗话》《白雨斋词话》《齐民要术》《武林旧事》《文史通义》《困学纪闻》的维基文库原文，
写入 sources/<slug>/chapters.json（格式同 tools/fetch_texts.py，由 tools/prepare_texts.py 配合 annotations 生成 src/），
并把页首提要（如有）并入 sources/wiki_intros.json。

  python3 tools/fetch_new7.py [slug ...]

与 fetch_texts.py 的不同：作者自注（页面上以〈…〉标出的小字）保留在原文里，不删；
只有标题里被截断的〈…（如“种谷第三〈稗附出…”）取〈之前作节名。
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
from fetch_orig import items            # 保留〈…〉
from fetch_texts import build_sections, lead

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
    return wiki, [(l, re.sub(r"〈[^〉]*〉?", "", t).strip() if l else t) for l, t in items(root)], str(page["revid"])


def sections(seq, mode, ptitle):
    """mode: headings | single | chunk=N。无意义的序号标题（一、二…）改取首句。"""
    if mode == "single":
        return [{"title": ptitle, "level": 2, "path": [], "author": "",
                 "paragraphs": [t for l, t in seq if l == 0]}]
    secs = build_sections(seq, mode, ptitle)
    for s in secs:
        if re.fullmatch(r"[〇一二三四五六七八九十]+", s["title"]) and s["paragraphs"]:
            s["title"] = lead(s["paragraphs"][0])
    return secs


def entry(slug, title, wiki, rev, secs):
    return {"slug": slug, "title": title, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
            "revision": rev, "heads": [], "sections": secs}


BOOKS = {
    "xingmingguizhi": ("性命圭旨", [("j1", "元集", "性命圭旨/元集", "headings"), ("j2", "亨集", "性命圭旨/亨集", "headings"),
                                 ("j3", "利集", "性命圭旨/利集", "headings"), ("j4", "贞集", "性命圭旨/貞集", "headings")]),
    "canglangshihua": ("滄浪詩話", [(f"j{n}", f"卷{num(n)}", f"滄浪詩話/卷{n}", "headings") for n in range(1, 6)]
                                  + [("x1", "附录", "滄浪詩話/附录", "single")]),
    "baiyuzhaicihua": ("白雨齋詞話", [("x1", "叙", "白雨齋詞話/0", "headings")]
                                    + [(f"j{n}", f"卷{num(n)}", f"白雨齋詞話/{n}", "headings") for n in range(1, 9)]
                                    + [("x2", "跋", "白雨齋詞話/9", "headings")]),
    "qiminyaoshu": ("齊民要術", [("x1", "李焘序", "齊民要術/序", "single"), ("x2", "自序", "齊民要術/自序", "single"),
                               ("x3", "杂说", "齊民要術/雜說", "single")]
                              + [(f"j{n}", f"卷第{num(n)}", f"齊民要術/卷第{num(n)}", "headings") for n in range(1, 11)]
                              + [("x4", "后序", "齊民要術/後序", "single")]),
    "wulinjiushi": ("武林舊事", [("x1", "序", "武林舊事/序", "single")]
                              + [(f"j{n}", f"卷{num(n)}", f"武林舊事/卷{num(n)}", "headings") for n in range(1, 11)]),
    "wenshitongyi": ("文史通義", [("x1", "章氏遗书序", "文史通義/序", "single")]
                               + [(f"j{n}", f"卷{num(n)}", f"文史通義/卷{n}", "headings") for n in range(1, 9)]),
    "kunxuejiwen": ("困學紀聞", [(f"j{n:02}", f"卷{num(n)}", f"困學紀聞/卷{n:02}", "chunk=8") for n in range(1, 21)]),
}


def intro_of(wiki_title):
    """页首提要：第二个 table 里的正文（与 wiki_intros.json 里已有各书的取法一致）。"""
    page = fetch(wiki_title, retries=8)
    soup = BeautifulSoup(page["text"], "html.parser")
    r = soup.select_one(".mw-parser-output")
    div = r.find("div", recursive=False)
    tbs = div.find_all("table", recursive=False) if div else []
    if len(tbs) < 2:
        return None, str(page["revid"])
    tb = tbs[1]
    for br in tb.find_all("br"):
        br.replace_with("\n")
    for p in tb.find_all("p"):
        p.append("\n")
    txt = re.sub(r"\[\d+\]", "", tb.get_text(""))
    txt = "\n".join(re.sub(r"\s+", "", l) for l in txt.split("\n") if l.strip())
    return txt, str(page["revid"])


def main():
    want = set(sys.argv[1:]) or set(BOOKS)
    wi_path = ROOT / "sources/wiki_intros.json"
    wi = json.loads(wi_path.read_text(encoding="utf8"))
    for slug, (wtitle, pages) in BOOKS.items():
        if slug not in want:
            continue
        out = []
        for pslug, ptitle, wiki, mode in pages:
            wiki2, seq, rev = seq_of(wiki)
            secs = sections(seq, mode, ptitle)
            secs = [s for s in secs if s["paragraphs"]]
            out.append(entry(pslug, ptitle, wiki2, rev, secs))
            print("  ", slug, pslug, ptitle, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        txt, rev = intro_of(wtitle)
        if txt and len(txt) > 60 and "姊妹计划" not in txt:
            wi[slug] = {"wikisource_title": wtitle, "revision": rev, "url": "https://zh.wikisource.org/zh-hans/" + quote(wtitle),
                        "text": txt, "verbatim": True}
            print("== intro", slug, len(txt))
    wi_path.write_text(json.dumps(wi, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
