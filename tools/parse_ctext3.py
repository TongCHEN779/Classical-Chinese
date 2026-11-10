#!/usr/bin/env python3
"""把缓存的中国哲学书电子化计划页面（sources/_ctext_cache/<chapter>.html）解析成 sources/<slug>/chapters.json。
《物理小识》（四库本，按卷、条）、《长物志》（四库本，无标点，按卷、类）、《园冶》（按卷、篇）。
繁体转简体用 opencc t2s；不校改文字。页面抓取见 README 说明：只手工低频抓取，避免触发 ctext 的验证码。
  python3 tools/parse_ctext3.py
"""
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import opencc

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "sources/_ctext_cache"
T2S = opencc.OpenCC("t2s")
CN = "零一二三四五六七八九十"


def num(n):
    return CN[n] if n <= 10 else ("十" + CN[n - 10] if n < 20 else CN[n // 10] + "十" + (CN[n % 10] if n % 10 else ""))


def rows(ch):
    s = BeautifulSoup((CACHE / f"{ch}.html").read_text(encoding="utf8"), "html.parser")
    for x in s.select("span.etext, span.libtarget"):
        x.decompose()
    for r in s.select("tr.result"):
        h = r.select_one("h2,h3,h4")
        if h:
            yield "H", h.name, h.get_text()
            continue
        tds = r.select("td.ctext")
        if tds:
            for a in tds[-1].select("a, div"):
                a.decompose()
            t = re.sub(r"\s+", "", tds[-1].get_text())
            if t:
                yield "P", None, t


def cv(t):
    return T2S.convert(t)


def entry(slug, title, ch, secs):
    return {"slug": slug, "title": title, "url": f"https://ctext.org/wiki.pl?if=gb&chapter={ch}",
            "revision": "ctext", "heads": [], "sections": secs}


def wulixiaoshi():
    ids = {1: 161215, 2: 946758, 3: 779094, 4: 355872, 5: 759303, 6: 866908, 7: 999808, 8: 481513, 9: 160695, 10: 206024, 11: 212519, 12: 103230}
    out = []
    for n, ch in ids.items():
        secs, cur = [], None
        for k, a, t in rows(ch):
            if k == "H":
                t = re.sub(r"[《》]", "", t)
                t = re.sub(r"\s+[A-Za-z].*$", "", t.strip())
                if a == "h2":
                    group = t
                    cur = None
                else:
                    cur = {"title": cv(t.split("·", 1)[-1]), "level": 3, "path": [cv(group)], "author": "", "paragraphs": []}
                    secs.append(cur)
            elif cur is not None:
                cur["paragraphs"].append(cv(t.lstrip("○")))
            else:
                raise SystemExit(f"卷{n}：条目前的正文 {t[:20]}")
        secs = [s for s in secs if s["paragraphs"]]
        out.append(entry(f"j{n}", f"卷{num(n)}", ch, secs))
    return out


def changwuzhi():
    ids = [("x1", "序", 851383)] + [(f"j{n}", f"卷{num(n)}", c) for n, c in zip(
        range(1, 13), [915870, 86895, 667423, 585226, 457120, 185690, 746416, 626697, 494280, 73455, 733604, 267156])]
    out = []
    for slug, title, ch in ids:
        secs, cur = [], None
        for k, a, t in rows(ch):
            if k == "H":
                continue
            t = cv(t)
            if slug == "x1":
                if t.startswith("序《四库全书") or t in ("钦定四库全书", "子部十", "长物志", "杂家类四", "杂品之属"):
                    continue
                if cur is None:
                    cur = {"title": "序", "level": 2, "path": [], "author": "", "paragraphs": []}
                    secs.append(cur)
                cur["paragraphs"].append(t)
                continue
            if t.startswith("○"):
                cur = {"title": t[1:], "level": 2, "path": [], "author": "", "paragraphs": []}
                secs.append(cur)
            elif cur is not None:
                cur["paragraphs"].append(t)
            # 卷首“（明）文震亨 撰”之类署名行丢弃
        out.append(entry(slug, title, ch, [s for s in secs if s["paragraphs"]]))
    return out


def yuanye():
    """页：自序、卷一、卷二、卷三、自识（卷后）；节：ctext 的各篇标题。"""
    pages, cur, sec = [], None, None
    for k, a, t in rows(378683):
        if k == "H":
            continue
        t = cv(t)
        if t.replace(" ", "") in ("园冶明计成",):
            continue
        m = re.match(r"^卷([一二三])\s*(.+?)[。]?$", t)
        if t == "自序":
            cur = {"slug": "x1", "title": "自序", "secs": []}; pages.append(cur)
            sec = {"title": "自序", "level": 2, "path": [], "author": "", "paragraphs": []}; cur["secs"].append(sec)
        elif m:
            cur = {"slug": "j" + str("一二三".index(m.group(1)) + 1), "title": "卷" + m.group(1), "secs": []}; pages.append(cur)
            sec = {"title": m.group(2).strip("。"), "level": 2, "path": [], "author": "", "paragraphs": []}; cur["secs"].append(sec)
        elif re.fullmatch(r"卷[一二三]", t):
            cur = {"slug": "j" + str("一二三".index(t[1]) + 1), "title": t, "secs": []}; pages.append(cur); sec = None
        elif t == "卷后":
            cur = {"slug": "x2", "title": "自识", "secs": []}; pages.append(cur)
            sec = {"title": "自识", "level": 2, "path": [], "author": "", "paragraphs": []}; cur["secs"].append(sec)
        elif cur and re.match(r"^[一二三四五六七八九十]+、", t) and len(t) <= 8:
            sec = {"title": t, "level": 2, "path": [], "author": "", "paragraphs": []}; cur["secs"].append(sec)
        elif sec is not None:
            sec["paragraphs"].append(t)
    return [entry(p["slug"], p["title"], 378683, [x for x in p["secs"] if x["paragraphs"]]) for p in pages]


if __name__ == "__main__":
    for slug, fn in [("wulixiaoshi", wulixiaoshi), ("changwuzhi", changwuzhi), ("yuanye", yuanye)]:
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        data = fn()
        (d / "chapters.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print(slug, [(p["slug"], len(p["sections"]), sum(len(q) for s in p["sections"] for q in s["paragraphs"])) for p in data])
