#!/usr/bin/env python3
"""大般若波罗蜜多经（玄奘译，600卷）：取维基文库各卷原文，写入 sources/dabanruojing/chapters.json；只收原文，不配白话与注释。

  python3 tools/fetch_dabore.py fetch      取各卷（可断点续传）
  python3 tools/fetch_vernacular.py prepare dabanruojing   生成 src 与 pages.json
  python3 tools/fetch_dabore.py groups     给 pages.json 按“会”加分组标题（prepare 之后运行）

维基文库分九部分页：第一会 1–400 卷、第二三会 401–537、第四五会 538–565、第六会 566–573、第七会 574–575、第八会 576、第九会 577、第十会 578，
第十一至十六会 579–600（单卷页在“大般若波罗蜜多经/卷NNN”下）。
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
from fetch_orig import items
from fetch_quantangwen import sections_of
import fetch_vernacular as fv

OUT = ROOT / "sources/dabanruojing"
HUBS = [  # (维基页名, 起, 止, 分组名)
    ("大般若經第一會(上品般若)：第1卷至第400卷", 1, 400, "第一会 上品般若（第一至四百卷）"),
    ("大般若經第二三會(中品般若)：第401卷至第537卷", 401, 537, "第二、三会 中品般若（第四百零一至五百三十七卷）"),
    ("大般若經第四五會(小品般若)：第538卷至第565卷", 538, 565, "第四、五会 小品般若（第五百三十八至五百六十五卷）"),
    ("大般若經第六會(天王般若)：第566卷至第573卷", 566, 573, "第六会 天王般若（第五百六十六至五百七十三卷）"),
    ("大般若經第七會(文殊般若)：第574卷至第575卷", 574, 575, "第七会 文殊般若（第五百七十四至五百七十五卷）"),
    ("大般若經第八會(那伽室利般若)：第576卷", 576, 576, "第八会 那伽室利般若（第五百七十六卷）"),
    ("大般若經第九會(能斷金剛分)：第577卷", 577, 577, "第九会 能断金刚分（第五百七十七卷）"),
    ("大般若經第十會(般若理趣分)：第578卷", 578, 578, "第十会 般若理趣分（第五百七十八卷）"),
    ("大般若波羅蜜多經", 579, 600, "第十一至十六会 六波罗蜜多分（第五百七十九至六百卷）"),
]


def jobs():
    out = []
    for hub, a, b, grp in HUBS:
        for n in range(a, b + 1):
            if a == b:
                wt = hub                                     # 单卷会：页就是该卷
            elif hub == "大般若波羅蜜多經":
                wt = f"大般若波羅蜜多經/卷{n:03d}"
            else:
                wt = f"{hub}/卷{n:03d}"
            out.append((n, wt, grp))
    return out


def title_of(n):
    return "卷第" + fv.cn_num(n) if hasattr(fv, "cn_num") else "卷第" + cn(n)


def cn(n):
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    s = ""
    h, r = divmod(n, 100)
    if h:
        s += d[h] + "百"
    t, u = divmod(r, 10)
    if t:
        s += ("" if (t == 1 and not h) else d[t]) + "十"
    elif h and u:
        s += "零"
    if u:
        s += d[u]
    return s


def do_fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "chapters.json"
    done = {c["slug"]: c for c in json.loads(cache.read_text(encoding="utf8"))} if cache.exists() else {}
    js = jobs()
    for k, (n, wt, grp) in enumerate(js, 1):
        slug = f"p{n:03d}"
        if slug in done:
            continue
        try:
            page = fetch(wt, retries=8)
        except Exception as e:
            print("SKIP", n, wt, type(e).__name__, flush=True)
            continue
        root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
        refs = fv.refs_of(root)
        secs = sections_of(list(items(root)))
        if len(secs) == 1 and secs[0]["title"] in ("正文", ""):
            secs[0]["title"] = "卷第" + cn(n)
        done[slug] = {"slug": slug, "title": "卷第" + cn(n), "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wt),
                      "revision": str(page["revid"]), "heads": [], "sections": secs, **({"refs": refs} if refs else {})}
        print(n, sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
        if k % 20 == 0:
            cache.write_text(json.dumps(sorted(done.values(), key=lambda c: c["slug"]), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    cache.write_text(json.dumps(sorted(done.values(), key=lambda c: c["slug"]), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("共", len(done), "卷")


def do_groups():
    pj = OUT / "pages.json"
    pages = json.loads(pj.read_text(encoding="utf8"))
    by_n = {n: grp for n, _wt, grp in jobs()}
    for p in pages:
        p[2] = by_n[int(p[0][1:])]
    pj.write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(len(pages), "页已分组")


if __name__ == "__main__":
    {"fetch": do_fetch, "groups": do_groups}[sys.argv[1] if len(sys.argv) > 1 else "fetch"]()
