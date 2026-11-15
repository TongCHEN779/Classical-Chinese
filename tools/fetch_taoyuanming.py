#!/usr/bin/env python3
"""缓存维基文库《陶渊明集》（序与卷之一至卷之七）：写入 sources/taoyuanmingji/chapters.json。

  python3 tools/fetch_taoyuanming.py [CACHE_DIR]     CACHE_DIR 里若已有 <标题>.json（API 原始返回，/ 换成 _）则不再联网

页：序、卷之一（诗四言）至卷之七（疏祭文）；每篇（二级标题）一节，组诗（三级标题“其一…”）每首一节，节名“篇名·其一”；
诗按阕（空行分隔）成段，每阕各行首尾相接成一段；诗前的小序作为该节第一段（"verse_from" 为小序段数，其余段为诗行，居中显示）。
“一作…”的异文夹注从正文移出，记在节的 "variants" 里（{p: 段下标, w: 被注字词, v: 异文}），写注释时补入。
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_shihua import raw_page

CN = "一二三四五六七"
TITLES = {1: "卷之一·诗四言", 2: "卷之二·诗", 3: "卷之三·诗五言", 4: "卷之四·诗五言", 5: "卷之五·赋辞", 6: "卷之六·记传赞述", 7: "卷之七·疏祭文"}


def clean_root(page):
    r = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    for x in r.select("table, .noprint, style, .licenseContainer, sup.reference, ol.references, link"):
        x.decompose()
    return r


def block_paras(el):
    """返回 (段落列表, 异文列表[(段下标, 字词, 异文)])。el 是 p 或 div.poem。"""
    variants_raw = []
    for vt in el.select(".variant-text"):
        tip = vt.select_one(".variant-tooltip")
        v = tip.get_text(strip=True) if tip else ""
        if tip:
            tip.decompose()
        vt.replace_with(f"␁{len(variants_raw)}␂" + vt.get_text("") + "␃")
        variants_raw.append(v)
    for br in el.find_all("br"):
        br.replace_with("\n")
    text = el.get_text("")
    blocks = [b for b in re.split(r"\n\s*\n", text.strip())]
    paras, variants, nlines = [], [], []
    for b in blocks:
        lines = [l.strip() for l in b.split("\n") if l.strip()]
        if not lines:
            continue
        t = "".join(lines)
        for m in re.finditer("␁(\\d+)␂(.*?)␃", t):
            variants.append((len(paras), m.group(2), variants_raw[int(m.group(1))]))
        t = re.sub("␁\\d+␂(.*?)␃", r"\1", t)
        t = re.sub(r"\s+", "", t)
        paras.append(t)
        nlines.append(len(lines))
    return paras, variants, nlines


def blocks_in(el):
    """el 内的正文块：自身是 p，或其中的各个 p（嵌套在 center/div.poem/div.Kaiti 里）；返回 [(元素, 是否在 .poem 内)]。"""
    if el.name == "p":
        return [(el, "poem" in (el.get("class") or []))]
    out = []
    for p in el.find_all("p"):
        if p.find("p"):
            continue
        out.append((p, any("poem" in (a.get("class") or []) for a in p.parents)))
    if not out and el.get_text(strip=True):
        out.append((el, "poem" in (el.get("class") or [])))
    return out


def parse_page(page, ptitle):
    root = clean_root(page)
    secs, cur, parent = [], None, None
    for el in root.children:
        if not getattr(el, "name", None) or el.name in ("style", "meta", "link"):
            continue
        cls = el.get("class") or []
        if "mw-heading" in cls:
            h = el.find(re.compile("h[1-6]"))
            name = re.sub(r"\s+", "", h.get_text(strip=True))
            if h.name == "h2":
                parent = name
                cur = {"title": name, "level": 3, "path": [ptitle], "author": "", "paragraphs": [], "variants": [], "nl": [], "poem": []}
                secs.append(cur)
            elif h.name == "h3":
                if secs and not secs[-1]["paragraphs"] and secs[-1]["title"] == parent:
                    secs.pop()          # 组诗标题本身没有正文：去掉，只留各首
                cur = {"title": f"{parent}·{name}", "level": 3, "path": [ptitle], "author": "", "paragraphs": [], "variants": [], "nl": [], "poem": []}
                secs.append(cur)
        elif cur is not None:
            for blk, in_poem in blocks_in(el):
                ps, vs, nl = block_paras(blk)
                base = len(cur["paragraphs"])
                cur["paragraphs"] += ps
                cur["variants"] += [(base + i, w, v) for i, w, v in vs]
                cur["nl"] += nl
                cur["poem"] += [in_poem] * len(ps)
    return secs


def main():
    cache = sys.argv[1] if len(sys.argv) > 1 else None
    out = []
    xu = raw_page("陶淵明集/序", cache)
    r = clean_root(xu)
    paras = []
    for el in r.children:
        if getattr(el, "name", None) in ("p",) or "poem" in (getattr(el, "get", lambda *_: [])("class") or []):
            ps, _v, _n = block_paras(el)
            paras += ps
    out.append({"slug": "x1", "title": "序", "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote("陶淵明集/序"), "revision": str(xu["revid"]), "heads": [],
                "sections": [{"title": "序", "level": 3, "path": ["序"], "author": "", "paragraphs": paras, "variants": [], "verse_from": len(paras)}]})
    for n in range(1, 8):
        wiki = f"陶淵明集/卷{CN[n - 1]}"
        page = raw_page(wiki, cache)
        secs = parse_page(page, TITLES[n])
        for s in secs:
            # 诗行段：在 .poem 里的段，以及《读史述九章》各首；其前的单行长段是小序
            verse = [bool(x) for x in s["poem"]]
            if s["title"].startswith("读史述九章·"):
                verse = [True] * len(verse)
            if s["paragraphs"] and re.fullmatch(r"〈[^〉]*〉", s["paragraphs"][0]):      # 维基文库标的异题说明，不是正文
                s["title_note"] = s["paragraphs"][0]
                for key in ("paragraphs", "nl", "poem"):
                    s[key] = s[key][1:]
                verse = verse[1:]
                s["variants"] = [(p_ - 1, w, v) for p_, w, v in s["variants"] if p_ > 0]
            k = 0
            name0 = s["title"].split("·")[0]
            if verse and verse[0] and re.match(re.escape(name0) + r"，[^。]{0,14}也。", s["paragraphs"][0]):      # 停云、时运、荣木的小序
                verse[0] = False
                k = 1
            import statistics
            while k < len(verse) - 2 and verse[k]:      # 诗前的小序：比其后各阕明显长的散文段
                rest = [len(x) for x in s["paragraphs"][k + 1:]]
                if len(s["paragraphs"][k]) >= 28 and len(s["paragraphs"][k]) >= 1.5 * statistics.median(rest):
                    verse[k] = False
                    k += 1
                else:
                    break
            if s["title"] == "癸卯岁十二月中作与从弟敬远":      # 整首诗只有一行，页面里不在诗框内
                verse = [True] * len(verse)
            if any(verse):
                first = verse.index(True)
                assert all(verse[first:]) or True
                s["verse_from"] = first
            else:
                s["verse_from"] = len(verse)
            s["verse_flags"] = verse
            s["variants"] = [{"p": p, "w": w, "v": v} for p, w, v in s["variants"] if "{{{" not in v]
            s.pop("nl"); s.pop("poem")
        out.append({"slug": f"j{n:02d}", "title": TITLES[n], "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(wiki),
                    "revision": str(page["revid"]), "heads": [], "sections": secs})
        print(f"j{n:02d}", TITLES[n], len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
    d = ROOT / "sources/taoyuanmingji"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("序", sum(len(p) for p in paras))


if __name__ == "__main__":
    main()
