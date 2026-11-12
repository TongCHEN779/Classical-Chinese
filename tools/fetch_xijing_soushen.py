#!/usr/bin/env python3
"""缓存《西京杂记》《搜神记》《玄怪录》的维基文库原文，写入 sources/<slug>/chapters.json（格式同 tools/fetch_books2.py），
并把页首提要并入 sources/wiki_intros.json。

  python3 tools/fetch_xijing_soushen.py [slug ...]

西京杂记：每条（页内标题“一、萧何营未央宫”）为一节；
搜神记：页内无条目标题，按段落贪心合并成约 G 字的一节，节名取首段开头几个字。
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
from fetch_texts import items
from fetch_books2 import units, sections, num
from fetch_new7 import intro_of

BOOKS = {
    "xijingzaji": {"wiki": "西京雜記", "g": 2200, "pages": (
        [(f"j{n}", f"卷{num(n)}", f"西京雜記/卷{'一二三四五六'[n - 1]}") for n in range(1, 7)])},
    "soushenji": {"wiki": "搜神記", "g": 1800, "pages": (
        [("x1", "序", "搜神記/序")]
        + [(f"j{n:02}", f"卷{num(n)}", f"搜神記/第{n:02}卷") for n in range(1, 21)])},
    "xuanguailu": {"wiki": "玄怪錄", "g": 2500, "pages": (
        [(f"j{n}", f"卷{num(n)}", f"玄怪錄/卷{n}") for n in range(1, 5)] + [("j5", "卷五·辑佚", "玄怪錄/卷5")])},
    # 续玄怪录：全文在一页，二级标题为卷，三级标题为各篇；按卷拆成页
    "xuxuanguailu": {"wiki": "續玄怪錄", "g": 2500, "by_parent": True, "pages": []},
}


def main():
    want = set(sys.argv[1:]) or set(BOOKS)
    wi_path = ROOT / "sources/wiki_intros.json"
    wi = json.loads(wi_path.read_text(encoding="utf8"))
    for slug, cfg in BOOKS.items():
        if slug not in want:
            continue
        out = []
        if cfg.get("by_parent"):
            page = fetch(cfg["wiki"], retries=8)
            root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
            groups = {}
            for title, parent, paras in units(list(items(root))):
                groups.setdefault(parent, []).append((title, "", paras))
            for k, (parent, us) in enumerate(groups.items(), 1):
                secs = sections(us, parent, cfg["g"], False)
                out.append({"slug": f"j{k}", "title": parent, "url": "https://zh.wikisource.org/zh-hans/" + quote(cfg["wiki"]),
                            "revision": str(page["revid"]), "heads": [], "sections": secs})
                print(slug, f"j{k}", parent, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
        for pslug, ptitle, wiki in cfg["pages"]:
            page = fetch(wiki, retries=8)
            root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
            secs = sections(units(list(items(root))), ptitle, cfg["g"], False)
            out.append({"slug": pslug, "title": ptitle, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
                        "revision": str(page["revid"]), "heads": [], "sections": secs})
            print(slug, pslug, ptitle, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        txt, rev = intro_of(cfg["wiki"])
        txt = re.sub(r"\n维基百科条目：[^\n]*$", "", re.sub(r"姊妹计划:.*$", "", re.sub(r"^维基百科条目：[^\n]*\n", "", txt or ""))).strip()
        print("== intro", slug, len(txt or ""), (txt or "")[:80])
        if txt and len(txt) > 30:
            wi[slug] = {"wikisource_title": cfg["wiki"], "revision": rev,
                        "url": "https://zh.wikisource.org/zh-hans/" + quote(cfg["wiki"]),
                        "text": txt, "verbatim": True}
    wi_path.write_text(json.dumps(wi, ensure_ascii=False, indent=1), encoding="utf8")  # 与既有文件一致：无末尾换行


if __name__ == "__main__":
    main()
