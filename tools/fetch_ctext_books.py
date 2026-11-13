#!/usr/bin/env python3
"""维基文库没有的几部书，改取中国哲学书电子化计划（ctext）的原文：北宋志传、型世言。

  python3 tools/fetch_ctext_books.py [slug ...]

写入 sources/<slug>/chapters.json（格式同 tools/fetch_vernacular.py，由其 prepare 步骤生成 src 与 pages.json）。
ctext 对高频抓取会出验证码，所以每页间隔数秒；繁体转简体用 opencc t2s，不校改文字。ctext 上这几部是机器识别的电子本，未经校对，页面末注明。
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
import opencc

ROOT = Path(__file__).resolve().parents[1]
T2S = opencc.OpenCC("t2s")
UA = "Mozilla/5.0 (ClassicalChinesePublicDomainLibrary; low-frequency research fetch)"
# slug: (书名, ctext 书目页 res 编号, ctext 页内书名)
BOOKS = {
    "beisongzhizhuan": ("北宋志传", 212529),
    "xingshiyan": ("型世言", 774409),
}
# 宝剑记（res=98311）、鸣凤记（res=111435）在 ctext 上是未校对的机器识别文字，实测满篇乱码（如“寶劍記序新文藝出版社藏書琵琶記冠絕諸戯文自斟卜艾鄉剛己北睡值湛審開”），不可用，故不收。


def get(url, retries=4):
    for k in range(retries):
        time.sleep(7)
        r = subprocess.run(["curl", "-sL", "-m", "45", "-A", UA, url], capture_output=True, text=True)
        if r.returncode == 0 and len(r.stdout) > 3000 and "captcha" not in r.stdout.lower()[:20000]:
            return r.stdout
        time.sleep(20 * (k + 1))
    raise RuntimeError("fetch failed " + url)


def index_of(slug):
    title, res = BOOKS[slug]
    if res is None:
        h = get(f"https://ctext.org/wiki.pl?if=gb&chapter={FIRST_CHAPTER[slug]}")
        m = re.search(r"wiki\.pl\?(?:if=\w+&(?:amp;)?)?res=(\d+)", h)
        res = int(m.group(1))
        print("res", res, flush=True)
    h = get(f"https://ctext.org/wiki.pl?if=gb&res={res}")
    s = BeautifulSoup(h, "html.parser")
    out, seen = [], set()
    for a in s.select("a[href*='chapter=']"):
        m = re.search(r"chapter=(\d+)", a["href"])
        t = re.sub(r"\s+", " ", a.get_text()).strip()
        if m and m.group(1) not in seen and t:
            seen.add(m.group(1))
            out.append((m.group(1), re.sub(r"^\d+\.\s*", "", t)))
    return out, res


def rows(h):
    s = BeautifulSoup(h, "html.parser")
    for x in s.select("span.etext, span.libtarget"):
        x.decompose()
    for r in s.select("tr.result"):
        hd = r.select_one("h2,h3,h4")
        if hd:
            yield "H", hd.get_text()
            continue
        tds = r.select("td.ctext")
        if tds:
            for a in tds[-1].select("a, div"):
                a.decompose()
            t = re.sub(r"\s+", "", tds[-1].get_text())
            if t:
                yield "P", t


def main():
    want = set(sys.argv[1:]) or set(BOOKS)
    for slug, (title, _) in BOOKS.items():
        if slug not in want:
            continue
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        cache = d / "chapters.json"
        done = {c["slug"]: c for c in json.loads(cache.read_text(encoding="utf8"))} if cache.exists() else {}
        idx, res = index_of(slug)
        print(slug, title, len(idx), "页", flush=True)
        for i, (ch, label) in enumerate(idx, 1):
            pslug = f"p{i:03d}"
            if pslug in done:
                continue
            h = get(f"https://ctext.org/wiki.pl?if=gb&chapter={ch}")
            paras = [T2S.convert(t) for k, t in rows(h) if k == "P"]
            ptitle = re.sub(r"\s+", " ", T2S.convert(label)).strip()
            ptitle = re.sub(r"^第([0-9一二三四五六七八九十百零〇]+)([回出折])\s+", r"第\1\2 ", ptitle)
            if not paras:
                print("EMPTY", slug, pslug, ptitle, flush=True)
                continue
            done[pslug] = {"slug": pslug, "title": ptitle, "head": "", "url": f"https://ctext.org/wiki.pl?if=gb&chapter={ch}",
                           "revision": "ctext", "heads": [],
                           "sections": [{"title": ptitle, "level": 3, "path": [], "author": "", "paragraphs": paras}]}
            print(slug, pslug, ptitle[:24], len(paras), sum(len(p) for p in paras), flush=True)
            if i % 10 == 0:
                cache.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        cache.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
