#!/usr/bin/env python3
"""由 sources/<book>/chapters.json（tools/fetch_orig.py 抓取的维基文库原文）生成只录原文的 src/<book>/<页>/01.txt，
并写 sources/<book>/pages.json（页表 [slug, 页面标题, 分组]）与 chapters.json 里的最终页名、节名。

  python3 tools/prepare_orig.py [book ...]

处理：
  水经注　保留〈…〉（郦注，小字显示）；
  后汉书、汉书　去掉〈…〉（李贤注、颜师古注，不是正文）；
  太平广记　去掉〈…〉里的校勘语，保留〈出…〉〈见…〉之类的出处。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIG_BOOKS = ["shuijingzhu", "houhanshu", "hanshu", "taipingguangji", "sanguozhi", "jinshu", "nanshi", "beishi", "suishu", "songshu",
              "nanqishu", "liangshu", "chenshu", "weishu", "beiqishu", "zhoushu", "jiutangshu", "xintangshu", "jiuwudaishi",
              "xinwudaishi", "liaoshi", "jinshi", "yuanshi", "mingshi", "songshi", "tongdian", "wenxiantongkao", "ershierzhaji"]
NOTE = re.compile(r"〈[^〈〉]*〉")


def strip_all(t):
    while NOTE.search(t):
        t = NOTE.sub("", t)
    return t


def strip_collation(t):
    """太平广记：〈出《神仙传》〉这类出处保留，其余〈…〉（校勘记）删去。"""
    return NOTE.sub(lambda m: m.group(0) if re.match(r"〈(出|见|录)", m.group(0)) else "", t)


def strip_review(t):
    """宋史：志里的小注是原书的，保留；〈案…〉〈按…〉〈考证〉之类的校语删去。"""
    return NOTE.sub(lambda m: "" if re.match(r"〈[（(]?(案|按|考证|校|臣)", m.group(0)) else m.group(0), t)


# 〈…〉小注的取舍：水经注（郦注）、通典（杜佑自注）、文献通考保留；宋史志文小注保留、校语删去；其余各书的〈…〉是后人的注、校勘、辑佚按语，不是正文，删去。
KEEP_NOTES = {"shuijingzhu", "tongdian", "wenxiantongkao"}
FILTERS = {b: (lambda t: t) for b in KEEP_NOTES}
FILTERS.update({"taipingguangji": strip_collation, "songshi": strip_review})


def clean_markup(t):
    """维基文库原页面里漏出来的 wiki 标记：[[链接|显示]]、{{模板|内容}}、残留的 /font> 之类，只留可见文字。"""
    t = re.sub(r"\[\[([^\[\]|]*\|)?([^\[\]]*)\]\]", r"\2", t)
    t = re.sub(r"\{\{[A-Za-z*]+\|([^{}]*)\}?\}?", r"\1", t)
    t = re.sub(r"\{?/(font|sub|sup|small|span)>", "", t)
    return t.replace("]]", "").replace("[[", "")


def clean_head(head):
    h = re.sub(r"\s*作者[:：].*$", "", head)
    return re.sub(r"[\s　]+", " ", h).strip()


BOOK_NAMES = {"shuijingzhu": "水经注", "houhanshu": "后汉书", "hanshu": "汉书", "taipingguangji": "太平广记"}
TRAIL_NUM = re.compile(r"[一二三四五六七八九十百]+$")


def page_title(book, head, link):
    """页面标题：取页眉里的卷号与篇名；页眉缺失时用目录页的链接文字。"""
    h = clean_head(head).replace("‧", " ").replace("·", " ")
    for name in (BOOK_NAMES.get(book), "后汉书", "汉书", "水经注", "太平广记", "三国志", "晋书"):
        if name and h.startswith(name + " "):
            h = h[len(name) + 1:]
            break
    toks = h.split()
    if not toks:
        return link
    if book == "taipingguangji":
        return f"{toks[0]}·{toks[1]}" if len(toks) > 1 else toks[0]
    if book == "shuijingzhu":
        names = [n for n in (re.sub(r"[〈〉]", "", t) for t in toks[1:]) if n]
        names = names[:3] + (["等"] if len(names) > 3 else [])
        vol = toks[0] if toks[0].startswith("卷") else "卷" + toks[0]
        return f"{vol}·{'、'.join(names[:3])}{names[3] if len(names) > 3 else ''}"
    if len(toks) == 1:
        return toks[0]
    rest = re.sub(r" (?=第)", "", " ".join(toks[1:])) if book != "shuijingzhu" else "、".join(toks[1:])
    return f"{toks[0]}·{rest}"


NO_GROUP = {"weishu", "ershierzhaji"}      # 目录页没有成体系的分类


def group_of(book, title, slug):
    if book == "taipingguangji":
        t = title.split("·", 1)[-1]
        return TRAIL_NUM.sub("", t) or t
    if book in ("houhanshu", "hanshu"):
        if re.search(r"叙例|校语|序$", title):
            return None
        if "《志》" in title or title.startswith("志第"):
            return "志"
        parts = title.split("·", 1)
        tok = re.sub(r"第.*$", "", parts[1].split()[0]) if len(parts) > 1 and parts[1].split() else ""
        return {"纪": "纪", "表": "表", "志": "志"}.get(tok[-1:], "传")
    if book in NO_GROUP:
        return None
    parts = title.split("·", 1)
    if len(parts) < 2:
        return None
    if not parts[1].split():
        return None
    tok = parts[1].split()[0]
    g = re.sub(r"[上中下]?第?[0-9一二三四五六七八九十百零〇]*[上中下]?$", "", tok)
    return g or None


def li_title(book, wiki, link, slug=""):
    """目录页里该条的整行文字：卷号、类目、人名/篇名。"""
    toc = ROOT / "sources" / book / "toc.json"
    if not toc.exists():
        return ""
    d = json.loads(toc.read_text(encoding="utf8"))
    return d.get(wiki) or d.get(slug, "")


def to_cn(m):
    sys.path.insert(0, str(ROOT / "tools"))
    from fetch_orig import num
    return num(int(m.group(0)))


def list_title(text, link):
    """“卷一 帝纪第一 高祖宣帝” → “卷一·帝纪第一 高祖宣帝”；阿拉伯数字改汉字，人名过多时只列前三个。"""
    t = re.sub(r"^\(\d+\)\s*", "", text).replace(":", " ").replace("：", " ")
    t = re.sub(r"\d+", to_cn, t)
    t = re.sub(r"\s+(?=第)", "", t) if not re.match(r"^第", t) else "志" + t
    toks = [x for x in t.replace("...", " ").split() if x != "…"]
    if not toks:
        return link
    if len(toks) > 1 and toks[1] == "补":
        toks = [toks[0] + "补"] + toks[2:]
    if len(toks) == 1:
        return toks[0]
    head, rest = toks[:2], toks[2:]
    tail = " ".join(rest[:3]) + (" 等" if len(rest) > 3 else "")
    return f"{head[0]}·{head[1]}" + (f" {tail}" if tail else "")


def table_lines(tb):
    out = ["表题：" + tb.get("cap", "")]
    if tb.get("head"):
        out.append("表头：" + "｜".join(tb["head"]))
    out += ["表行：" + "｜".join(r) for r in tb["rows"]]
    return out


def build(book):
    src = ROOT / "sources" / book / "chapters.json"
    chapters = json.loads(src.read_text(encoding="utf8"))
    filt = FILTERS.get(book, strip_all)
    pages = []
    out_dir = ROOT / "src" / book
    for ch in chapters:
        old = ch["title"]
        wiki = ch["url"].split("/zh-hans/", 1)[1]
        from urllib.parse import unquote
        li = li_title(book, unquote(wiki), old, ch['slug'])
        if li:
            title = list_title(li, old)
        else:
            title = page_title(book, ch.get("head", ""), old)
        secs = []
        for s in ch["sections"]:
            paras = [clean_markup(filt(p)).strip() for p in s["paragraphs"]]
            paras = [p for p in paras if re.search(r"[一-鿿]", p)]
            if not paras and not s.get("tables"):
                continue
            st = title if s["title"].endswith("…") or s["title"] == old else s["title"]
            secs.append({**s, "title": st, "paragraphs": paras})
        if not secs:
            print("EMPTY", book, ch["slug"], title)
            continue
        ch["title"], ch["sections"] = title, secs
        d = out_dir / ch["slug"]
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        for s in secs:
            lines.append("# " + s["title"])
            lines += ["原：" + p for p in s["paragraphs"]]
            for tb in s.get("tables", []):
                lines += table_lines(tb)
            lines.append("")
        (d / "01.txt").write_text("\n".join(lines), encoding="utf8")
        pages.append([ch["slug"], title, group_of(book, title, ch["slug"])])
    from collections import Counter
    cnt = Counter(p[2] for p in pages if p[2])
    last = None
    for p in pages:
        if p[2] and cnt[p[2]] < 2 and book not in ("taipingguangji",):
            p[2] = last
        last = p[2] or last
    first = next((i for i, p in enumerate(pages) if p[1].startswith("卷") and "·" in p[1]), None)
    if first is not None and book not in NO_GROUP:      # 排在各卷之后的序跋、附录等单页，归入“附录”组，免得挂在末一组下面
        for p in pages[first:]:
            if not p[1].startswith("卷") and "·" not in p[1] and not p[0].startswith("j"):
                p[2] = "附录"
    chapters = [c for c in chapters if any(c["slug"] == p[0] for p in pages)]
    src.write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (ROOT / "sources" / book / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(book, len(pages), "页", sum(len(p) for c in chapters for s in c["sections"] for p in s["paragraphs"]), "字")


if __name__ == "__main__":
    for b in sys.argv[1:] or ORIG_BOOKS:
        build(b)
