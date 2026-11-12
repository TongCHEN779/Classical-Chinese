#!/usr/bin/env python3
"""缓存维基文库《全唐文》（嘉庆十九年敕撰，董诰等编，一千卷）原文，写入 sources/quantangwen/chapters.json，
并生成 src/quantangwen/<页>/01.txt 与 sources/quantangwen/pages.json（供 build.py 的 _orig_spec 使用）。

  python3 tools/fetch_quantangwen.py [fetch|prepare]      默认两步都做；fetch 可断点续传（按已缓存的页跳过）

维基文库的各卷页面只是目录，各篇正文是另立的页面、嵌入卷页，所以直接取卷页渲染后的 HTML 即得全卷正文。
小注（页面上以小字显示、前后有隐形〈〉的出处与校记）保留〈…〉，由 build.py 渲成小字灰色。
卷首（御制序、凡例、职名、进表）单独成页。各篇尚未录入维基文库的，卷页上只有标题而无正文，这样的篇目从略。
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
from fetch_orig import items, num as _num

def num(n):
    return "一千" if n == 1000 else _num(n)


BOOK = "quantangwen"
OUT = ROOT / "sources" / BOOK
NOTE = re.compile(r"〈[^〈〉]*〉")
FRONT = [("x1", "御制全唐文序", "御製全唐文序"), ("x2", "御制读全唐文", "御製讀全唐文"), ("x3", "凡例", "全唐文凡例"),
         ("x4", "职名", "全唐文職名"), ("x5", "进全唐文表", "進全唐文表")]


def toc():
    """[(卷号, 页面标题, 维基标题)]，页面标题取自总目录页上的“卷一 高祖”。"""
    page = fetch("全唐文", retries=8)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    out = {}
    for a in root.select("a"):
        m = re.match(r"/wiki/全唐文/卷(\d{4})$", unquote(a.get("href", "")))
        li = a.find_parent("li")
        if m and li:
            n = int(m.group(1))
            t = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
            t = re.sub(r"^卷[一二三四五六七八九十百千零〇]+ ", "", t)
            out[n] = (n, f"卷{num(n)}·{t}", f"全唐文/卷{n:04d}")
    return [out[n] for n in sorted(out)]


def tidy_title(t):
    t = NOTE.sub("", t)
    return re.sub(r"\s+", " ", t.replace("​", "")).strip()


def sections_of(seq):
    """seq 为 items() 的输出。每个有正文的标题为一节；卷内作者不止一位时节名前冠作者名。"""
    seq = [(l, t.replace("​", "").strip()) for l, t in seq]
    seq = [(l, t) for l, t in seq if t]
    units, trail, cur = [], [], None
    skip = False
    for lvl, t in seq:
        if lvl:
            skip = bool(re.search(r"目录$|目錄$", t))
            if skip:
                continue
            while trail and trail[-1][0] >= lvl:
                trail.pop()
            parent = trail[-1][1] if trail else ""
            trail.append((lvl, t))
            cur = {"title": tidy_title(t), "parent": tidy_title(parent), "paragraphs": []}
            units.append(cur)
        elif not skip:
            if cur is None:
                cur = {"title": "", "parent": "", "paragraphs": []}
                units.append(cur)
            cur["paragraphs"].append(t)
    units = [u for u in units if u["paragraphs"]]
    parents = {u["parent"] for u in units if u["parent"]}
    multi = len(parents) > 1
    out = []
    for u in units:
        name = u["title"]
        if multi and u["parent"] and u["parent"] != u["title"]:
            name = f'{u["parent"]}·{u["title"]}'
        out.append({"title": name or "正文", "level": 3, "path": [], "author": "", "paragraphs": u["paragraphs"]})
    return out


def entry(slug, title, wiki, page, secs):
    return {"slug": slug, "title": title, "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
            "revision": str(page["revid"]), "heads": [], "sections": secs}


def do_fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "chapters.json"
    done = {c["slug"]: c for c in json.loads(cache.read_text(encoding="utf8"))} if cache.exists() else {}
    jobs = [(s, t, w) for s, t, w in FRONT] + [(f"j{n:04d}", t, w) for n, t, w in toc()]
    for i, (slug, title, wiki) in enumerate(jobs, 1):
        if slug in done:
            continue
        try:
            page = fetch(wiki, retries=8)
        except Exception as e:
            print("SKIP", slug, title, type(e).__name__, flush=True)
            continue
        root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
        secs = sections_of(list(items(root)))
        done[slug] = entry(slug, title, wiki, page, secs)
        print(slug, title, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
        if i % 20 == 0:
            cache.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    cache.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1) + "\n", encoding="utf8")


def clean_markup(t):
    t = re.sub(r"\[\[([^\[\]|]*\|)?([^\[\]]*)\]\]", r"\2", t)
    t = re.sub(r"\{\{[A-Za-z*]+\|([^{}]*)\}?\}?", r"\1", t)
    return t.replace("]]", "").replace("[[", "")


def do_prepare():
    chapters = json.loads((OUT / "chapters.json").read_text(encoding="utf8"))
    src = ROOT / "src" / BOOK
    pages, kept = [], []
    for ch in chapters:
        secs = []
        for s in ch["sections"]:
            paras = [clean_markup(p).strip() for p in s["paragraphs"]]
            paras = [p for p in paras if re.search(r"[一-鿿]", p)]
            if paras:
                secs.append({**s, "paragraphs": paras})
        if not secs:
            print("EMPTY", ch["slug"], ch["title"])
            continue
        ch["sections"] = secs
        d = src / ch["slug"]
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        for s in secs:
            lines.append("# " + s["title"])
            lines += ["原：" + p for p in s["paragraphs"]]
            lines.append("")
        (d / "01.txt").write_text("\n".join(lines), encoding="utf8")
        if ch["slug"].startswith("x"):
            grp = "卷首"
        else:
            n = int(ch["slug"][1:])
            lo = (n - 1) // 50 * 50 + 1
            grp = f"卷{num(lo)}至卷{num(lo + 49)}"
        pages.append([ch["slug"], ch["title"], grp])
        kept.append(ch)
    (OUT / "chapters.json").write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (OUT / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(BOOK, len(pages), "页", sum(len(p) for c in kept for s in c["sections"] for p in s["paragraphs"]), "字")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "both"
    if step in ("fetch", "both"):
        do_fetch()
    if step in ("prepare", "both"):
        do_prepare()
