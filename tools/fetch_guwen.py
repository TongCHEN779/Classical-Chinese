#!/usr/bin/env python3
"""缓存维基文库《古文辞类纂》《六朝文絜》（选本，每篇一个单页）：写入 sources/<slug>/chapters.json 与 entries.json。

  python3 tools/fetch_guwen.py [guwenciliezuan|liuchaowenjie ...] [--cache DIR]

目录页的每个二级标题是一卷（页），其下 li 是一篇（一节）：节名＝“篇名（作者）”；维基文库尚无页面的篇目（红链）不收，列入 entries.json 的 missing。
重定向页取目标页（可带 #上/#中/#下 之类锚点，按标题截取）；页内只取段落，不收页眉页脚。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, quote

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch
from fetch_orig import page_of, items, cut
import opencc

T2S = opencc.OpenCC("t2s")

BOOKS = {
    "guwenciliezuan": {"wiki": "古文辭類纂", "front": ("x1", "序", "古文辭類纂/序")},
    "liuchaowenjie": {"wiki": "六朝文絜", "front": ("x1", "六朝文絜原序", "六朝文絜原序")},
}
CN = "零一二三四五六七八九十"


def cnum(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n - 10] if n > 10 else "")
    t, u = divmod(n, 10)
    return CN[t] + "十" + (CN[u] if u else "")


def norm(s):
    return re.sub(r"\s+", " ", s.replace("　", " ")).strip()


NOISE = re.compile(r"^(<\s*\S+\s*)+$|^[^，。]{2,10}/卷[一二三四五六七八九十]+$")      # 页眉页脚漏出的面包屑（“< 苏轼 < 古文观止”“东坡志林/卷五”）


def essay(wiki, frag, cache):
    key = cache / (wiki.replace("/", "_") + "#" + frag + ".json")
    if key.exists():
        return json.loads(key.read_text(encoding="utf8"))
    w, p, soup, f2 = page_of(wiki)
    frag = frag or f2
    root = soup.select_one(".mw-parser-output")
    for pre in root.find_all("pre"):      # <pre> 里的正文不经页面的繁简转换：按空行拆段，转简体（opencc t2s）
        for chunk in reversed([c for c in re.split(r"\n\s*\n", pre.get_text()) if c.strip()]):
            np_ = soup.new_tag("p")
            np_.string = T2S.convert(re.sub(r"\s+", "", chunk))
            pre.insert_after(np_)
        pre.decompose()
    seq = list(items(root))
    if frag:
        seq = cut(seq, frag)
    paras = [t for lv, t in seq if lv == 0 and t and not NOISE.match(t)]
    if paras and paras[0].endswith("可以指："):      # 消歧义页（如“陈政事疏”）：当作无正文，改取 ctext
        paras = []
    heads = [t for lv, t in seq if lv]
    out = {"wiki": w, "frag": frag, "revision": str(p["revid"]), "paras": paras, "heads": heads}
    key.write_text(json.dumps(out, ensure_ascii=False), encoding="utf8")
    return out


def label_of(book, rest):
    """节名：古文辞类纂目录“作者　篇名”→“篇名（作者）”；六朝文絜“篇名(朝・作者)”统一用全角括号。"""
    if book == "guwenciliezuan":
        a, _, t = rest.partition(" ")
        return f"{t}（{a}）" if t else rest
    m = re.match(r"^(.+?)[(（]\s*(.+?)\s*[)）]$", rest)
    return f"{m.group(1)}（{re.sub(r'[·・]', '・', re.sub(r'\s+', '', m.group(2)))}）" if m else rest


def index_of(book, cache):
    cfg = BOOKS[book]
    p = fetch(cfg["wiki"], retries=8)
    root = BeautifulSoup(p["text"], "html.parser").select_one(".mw-parser-output")
    vols = []
    for h in root.select("div.mw-heading"):
        t = norm(h.get_text())
        ol = h.find_next_sibling()
        if not ol or ol.name != "ol":
            vols.append((t, None, []))
            continue
        ents = []
        for li in ol.find_all("li", recursive=False):
            a = li.find("a", href=re.compile(r"^/wiki/(?!Author:)")) or li.find("a", href=re.compile(r"redlink"))
            if a is None:
                continue
            title = norm(a.get_text())
            href = unquote(a["href"])
            red = "redlink=1" in href
            frag = ""
            wt = href[6:] if href.startswith("/wiki/") else re.search(r"title=([^&]+)", href).group(1)
            wt = wt.split("&")[0]
            if "#" in wt:
                wt, frag = wt.split("#", 1)
            rest = norm(li.get_text()).replace(title, "", 1).strip(" （()）・·")      # 作者：古文辞类纂在链接前（贾生　过秦论上），六朝文絜在链接后（（宋・鲍照））
            ents.append({"title": title, "wiki": wt.replace("_", " "), "frag": frag, "red": red, "rest": norm(li.get_text())})
        vols.append((t, ol, ents))
    return p, vols


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cache = Path(sys.argv[sys.argv.index("--cache") + 1]) if "--cache" in sys.argv else ROOT / "sources/_guwen_cache"
    if "--cache" in sys.argv:
        args = [a for a in args if a != str(cache)]
    cache.mkdir(parents=True, exist_ok=True)
    for book in args or list(BOOKS):
        cfg = BOOKS[book]
        mainp, vols = index_of(book, cache)
        out, entries, missing = [], [], []
        fp = ROOT / "sources" / book / "ctext_fill.json"
        fills = json.loads(fp.read_text(encoding="utf8")) if fp.exists() else {}
        slug, title, wiki = cfg["front"]
        e = essay(wiki, "", cache)
        out.append({"slug": slug, "title": title, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki), "revision": e["revision"], "heads": [],
                    "sections": [{"title": title, "level": 3, "path": [title], "author": "", "paragraphs": e["paras"]}]})
        n = 0
        for vt, ol, ents in vols:
            m = re.match(r"^卷([一二三四五六七八九十]+)", vt)
            if not m:
                continue
            n += 1
            secs = []
            for ent in ents:
                src = "wikisource"
                e = None if ent["red"] else essay(ent["wiki"], ent["frag"], cache)
                if e is None or not e["paras"]:      # 维基文库没有（红链）或页面无正文：取 ctext（字符识别本，未校对）
                    f_ = fills.get(f"{vt}|{ent['rest']}")
                    if not f_:
                        missing.append({"vol": vt, "entry": ent["rest"]} if e is None else {"vol": vt, "entry": ent["rest"], "note": "页面无正文"})
                        continue
                    e = {"wiki": f_["url"], "frag": "", "revision": "ctext", "paras": f_["paras"], "heads": []}
                    src = "ctext"
                label = label_of(book, ent["rest"])
                secs.append({"title": label, "level": 3, "path": [vt], "author": "", "paragraphs": e["paras"]})
                entries.append({"vol": n, "entry": label, "source": src, "wiki": e["wiki"], "frag": e["frag"], "revision": e["revision"], "heads": e["heads"]})
                print(book, vt, label, len(e["paras"]), flush=True)
            if secs:
                page_title = vt
                out.append({"slug": f"j{n:02d}", "title": page_title, "url": "https://zh.wikisource.org/zh-hans/" + quote(cfg["wiki"]), "revision": str(mainp["revid"]), "heads": [], "sections": secs})
        d = ROOT / "sources" / book
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        (d / "entries.json").write_text(json.dumps({"index_revision": str(mainp["revid"]), "entries": entries, "missing": missing}, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print(book, "卷", len(out) - 1, "篇", len(entries), "缺", len(missing), flush=True)


if __name__ == "__main__":
    main()
