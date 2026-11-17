#!/usr/bin/env python3
"""佛教典籍：金刚般若波罗蜜经（鸠摩罗什译）、般若波罗蜜多心经（玄奘译），取自维基文库，写入 sources/<slug>/chapters.json。

  python3 tools/fetch_fojing.py
金刚经：每分一节（节名“法会因由分第一”，维基文库节名后附的“‘说法聚会，由此起因’”之类提示语不要），
        不收维基文库页首的“南无本师…”“开经偈”和页尾“外部链接”（都不是译经本文）；段内因换行留下的空格去掉。
心经：三页——明太祖御制序、唐释慧忠序、玄奘译经文（到咒语为止）；页内另附的梵语咒文行与断句说明不收。
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

JING = "金剛般若波羅蜜經 (鳩摩羅什)"
XIN = "般若波羅蜜多心經 (玄奘)"


def seq_of(wiki):
    page = fetch(wiki, retries=8)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    return page, list(items(root))


def nospace(t):
    return re.sub(r"\s+", "", t)


def write(slug, wiki, page, title, secs):
    out = ROOT / "sources" / slug
    out.mkdir(parents=True, exist_ok=True)
    ch = [{"slug": "p01", "title": title, "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
           "revision": str(page["revid"]), "heads": [], "sections": secs}]
    (out / "chapters.json").write_text(json.dumps(ch, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(slug, len(secs), "节", sum(len(p) for s in secs for p in s["paragraphs"]), "字")


def main():
    page, seq = seq_of(JING)
    secs, cur = [], None
    for lvl, t in seq:
        if lvl == 4:
            cur = {"title": re.sub(r"[‘’].*$", "", t).strip(), "level": 3, "path": [], "author": "", "paragraphs": []}
            secs.append(cur)
        elif lvl and cur is not None:
            break                                   # “外部链接”
        elif lvl == 0 and cur is not None:
            cur["paragraphs"].append(nospace(t))
    assert len(secs) == 32, len(secs)
    write("jingangjing", JING, page, "金刚般若波罗蜜经", secs)

    page = fetch(XIN, retries=8)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    # 两篇序：明太祖御制序（h2）、唐释慧忠序（h1），标题在 .prp-pages-output 里，items() 看不到，直接读 DOM
    box = root.select_one(".prp-pages-output")
    heads = box.select(".mw-heading")
    assert len(heads) >= 2, len(heads)
    prefaces = []
    for hd, who in zip(heads[:2], ("", "（唐释慧忠撰）")):
        title = nospace(hd.get_text("")) + who
        p = hd.find_next_sibling("p")
        prefaces.append({"title": title, "level": 3, "path": [], "author": "", "paragraphs": [nospace(p.get_text(""))]})
    seq = list(items(root))
    texts = [t for _l, t in seq]
    i = next(k for k, t in enumerate(texts) if "唐三藏法师玄奘译" in t)
    j = next(k for k, t in enumerate(texts) if t.strip().startswith("“揭谛"))
    paras = [nospace(t) for t in texts[i + 1:j]] + [re.sub(r"\s+", " ", texts[j]).strip()]      # 咒语各词之间的空格保留
    sutra = {"title": "般若波罗蜜多心经", "level": 3, "path": [], "author": "", "paragraphs": paras}
    out = ROOT / "sources/xinjing"
    out.mkdir(parents=True, exist_ok=True)
    chs = [{"slug": sl, "title": s_["title"], "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(XIN),
            "revision": str(page["revid"]), "heads": [], "sections": [s_]} for sl, s_ in (("p01", prefaces[0]), ("p02", prefaces[1]), ("p03", sutra))]
    (out / "chapters.json").write_text(json.dumps(chs, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("xinjing", [c["title"] for c in chs], [len(c["sections"][0]["paragraphs"]) for c in chs])


if __name__ == "__main__":
    main()
