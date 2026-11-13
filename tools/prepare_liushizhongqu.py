#!/usr/bin/env python3
"""《六十种曲》（毛晋辑）：按维基文库总目录排列各剧。

  python3 tools/prepare_liushizhongqu.py toc        取总目录（含红链），写 sources/liushizhongqu/toc.json
  python3 tools/prepare_liushizhongqu.py build      由各剧已缓存的原文（sources/<slug>/chapters.json 或 lsz_*）拼成
                                                    sources/liushizhongqu/chapters.json、pages.json、missing.json 和 src/liushizhongqu/

每剧一页，页内以出（折）为节。维基文库没有页面、ctext 上又只有无法辨读的机器识别乱码的剧目，
不收原文，但仍在目录里保留条目（标“阙”）。与单独成书的传奇重复的剧目（如琵琶记）直接取同一份缓存。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "sources/liushizhongqu"
CN = "零一二三四五六七八九"

# 六十种曲里与单独成书的传奇同名的剧：维基文库页名 → 已缓存的书 slug
OVERLAP = {"琵琶記": "pipaji", "荊釵記": "jingchaiji", "荆釵記": "jingchaiji", "浣紗記": "huanshaji", "幽閨記": "youguiji", "玉簪記": "yuzanji",
           "紫釵記": "zichaiji", "邯鄲記": "handanji", "南柯記": "nankeji", "紅梨記": "hongliji", "紫簫記": "zixiaoji",
           "義俠記": "yixiaji", "白兔記": "baituji", "殺狗記": "shagouji", "東郭記": "dongguoji"}


# 维基文库上这几个页名是重定向（北西廂→北西廂記、南西廂→南西廂記、還魂記→牡丹亭），缓存在 lsz_ 书里
REDIRECT = {"北西廂": "lsz_beixixiang", "南西廂": "lsz_nanxixiang", "還魂記": "lsz_huanhunji"}


def cn(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n - 10] if n > 10 else "")
    return CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")


def do_toc():
    from fetch_wenxuan import fetch
    page = fetch("六十種曲", retries=8)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    out = []
    for a in root.select("a"):
        h = unquote(a.get("href", ""))
        red = "redlink=1" in h
        m = re.match(r"/wiki/([^#:]+)$", h) or re.search(r"title=([^&]+)&action=edit&redlink=1", h)
        if m and a.get_text().strip() and a.get_text().strip() not in ("毛晋", "南词叙录", "姊妹计划"):
            wt = unquote(m.group(1)).replace("_", " ")
            if wt in ("南詞敘錄",) or any(x["wiki"] == wt for x in out):
                continue
            out.append({"title": a.get_text().strip(), "wiki": wt, "exists": not red})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "toc.json").write_text(json.dumps({"revision": str(page["revid"]), "plays": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(len(out), "剧", sum(not x["exists"] for x in out), "红链")


def load_book(slug):
    p = ROOT / "sources" / slug / "chapters.json"
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else None


def lsz_slug(wiki):
    sys.path.insert(0, str(ROOT / "tools"))
    import fetch_vernacular as fv
    for s, (_t, w, _m) in fv.BOOKS.items():
        if s.startswith("lsz_") and w == wiki:
            return s
    return None


def do_build():
    toc = json.loads((OUT / "toc.json").read_text(encoding="utf8"))["plays"]
    chapters, pages, missing = [], [], []
    for i, pl in enumerate(toc, 1):
        slug = f"p{i:02d}"
        appendix = pl["wiki"] == "碩園訂本還魂記"
        group = "附" if appendix else f"第{cn((i - 1) // 5 + 1)}集"
        book = load_book(OVERLAP.get(pl["wiki"]) or REDIRECT.get(pl["wiki"]) or lsz_slug(pl["wiki"]) or "") if pl["exists"] else None
        title = pl["title"]
        if not book:
            pages.append([slug, title, group])
            missing.append(slug)
            print("阙", i, title)
            continue
        book.sort(key=lambda c: c["slug"])
        secs, revs = [], []
        for ch in book:
            for s in ch["sections"]:
                paras = [p for p in s["paragraphs"] if re.search(r"[一-鿿]", p)]
                if paras:
                    secs.append({"title": s["title"] or ch["title"], "level": 3, "path": [], "author": "", "paragraphs": paras})
            revs.append(ch["revision"])
        # 个别剧本（如还魂记）只有首出带“第X出”，其余只有出名：按序补上
        if secs and sum(bool(re.match(r"第.{1,4}[出齣折]", x["title"])) for x in secs) * 2 < len(secs):
            for k, x in enumerate(secs, 1):
                if not re.match(r"第.{1,4}[出齣折]", x["title"]):
                    x["title"] = f"第{cn(k)}出 {x['title']}"
        if not secs or sum(len(p) for x in secs for p in x["paragraphs"]) < 5000:     # 维基文库上只有零星片段（如昙花记）的，不当作全剧收
            pages.append([slug, title, group])
            missing.append(slug)
            print("阙(空)", i, title)
            continue
        d = ROOT / "src/liushizhongqu" / slug
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        for s in secs:
            lines.append("# " + s["title"])
            lines += ["原：" + p for p in s["paragraphs"]]
            lines.append("")
        (d / "01.txt").write_text("\n".join(lines), encoding="utf8")
        chapters.append({"slug": slug, "title": title, "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(pl["wiki"]),
                         "revision": revs[0], "heads": [], "sections": secs})
        pages.append([slug, title, group])
        print("收", i, title, len(secs), "节", sum(len(p) for s in secs for p in s["paragraphs"]), "字")
    (OUT / "chapters.json").write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (OUT / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (OUT / "missing.json").write_text(json.dumps(missing, ensure_ascii=False) + "\n", encoding="utf8")
    print("共", len(pages), "条，已收", len(chapters), "，暂缺", len(missing))


if __name__ == "__main__":
    {"toc": do_toc, "build": do_build}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
