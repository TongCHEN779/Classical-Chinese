#!/usr/bin/env python3
"""《笑得好》初集、二集：取维基文库页面，生成 sources/xiaodehao1|2|1w|2w/chapters.json。

  xiaodehao1/xiaodehao2：底本正文。页末“注释”一节（校勘性脚注）改为就地并入正文，写成“〈注：……〉”（标题上的脚注并到该则开头）；
                         标题上的小注（{{*|…}}，如“要学哭声才发笑”“笑吃人不请人的”）原先被节名清理掉了，现在作为该则第一行“〈…〉”保留。
  xiaodehao1w/2w：      初集、二集各自的“网传版本”（底本里没有的网传简体版文字），单页，每则一节。
用法：python3 tools/fetch_xiaodehao.py   然后 python3 tools/fetch_vernacular.py prepare xiaodehao1 xiaodehao2 xiaodehao1w xiaodehao2w
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch
from fetch_orig import items
from fetch_quantangwen import sections_of

BOOKS = {"xiaodehao1": "笑得好初集", "xiaodehao2": "笑得好二集"}
SHORT_TITLE = re.compile(r"^[^。！？，：；“”‘’]{1,14}(\(.*\))?$")


def ref_text(li):
    box = li.select_one(".reference-text") or li
    for x in box.select("sup.reference"):
        x.decompose()
    return re.sub(r"\s+", "", box.get_text("")).strip()


def one(wiki):
    page = fetch(wiki, retries=8)
    soup = BeautifulSoup(page["text"], "html.parser")
    root = soup.select_one(".mw-parser-output")
    notes = {li.get("id"): ref_text(li) for li in root.select("ol.references li")}
    # 从“网传版本”标题起到页尾：取出 blockquote，其余丢掉
    web = None
    for el in root.find_all("div", class_="mw-heading", recursive=False):
        if el.get_text("").strip().startswith(("网传版本", "網傳版本")):
            for nxt in el.find_next_siblings():
                if nxt.name == "blockquote" and web is None:
                    web = nxt.extract()
            for nxt in list(el.find_next_siblings()):
                nxt.decompose()
            el.decompose()
            break
    assert web is not None, wiki
    # 页内脚注：正文里的标号换成就地小注；标题里的标号并到该则开头
    def note_of(sup):
        a = sup.find("a")
        return notes.get((a.get("href") or "").lstrip("#"), "")
    for el in root.find_all("div", class_="mw-heading", recursive=False):
        h = el.find(re.compile("h[1-6]"))
        lead = []
        for small in h.find_all("small"):
            lead.append(re.sub(r"\s+", "", small.get_text("")))
        for sup in h.select("sup.reference"):
            t = note_of(sup)
            if t:
                lead.append(f"〈注：{t}〉")
            sup.decompose()
        if lead:
            p = soup.new_tag("p")
            p.string = "".join(lead)
            el.insert_after(p)
    for sup in root.select("sup.reference"):
        t = note_of(sup)
        sup.replace_with(NavigableString(f"〈注：{t}〉" if t else ""))
    for x in root.select("ol.references, .reflist, div.references-small"):
        x.decompose()
    secs = sections_of(list(items(root)))
    return page, secs, web


def web_sections(web):
    for x in web.select("table"):
        x.decompose()
    lines = [l.strip() for p in web.find_all("p") for l in p.get_text("").split("\n") if l.strip()]
    secs, cur = [], None
    for i, l in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if SHORT_TITLE.match(l) and nxt and not (SHORT_TITLE.match(nxt) and cur is not None and cur["paragraphs"] == []) and (cur is None or cur["paragraphs"]):
            m = re.match(r"^([^(]+)\((.*)\)$", l)
            title, note = (m.group(1), f"〈{m.group(2)}〉") if m else (l, "")
            cur = {"title": title, "level": 3, "path": [], "author": "", "paragraphs": [note] if note else []}
            if not note:
                cur["paragraphs"] = []
            secs.append(cur)
        elif cur is not None:
            cur["paragraphs"].append(l)
    return [s for s in secs if any("。" in p or "”" in p for p in s["paragraphs"])]


def entry(page, wiki, slug, title, secs):
    return {"slug": slug, "title": title, "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
            "revision": str(page["revid"]), "heads": [], "sections": secs}


def main():
    for slug, wiki in BOOKS.items():
        page, secs, web = one(wiki)
        out = ROOT / "sources" / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "chapters.json").write_text(json.dumps([entry(page, wiki, "p001", wiki, secs)], ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        ws = web_sections(web)
        wout = ROOT / "sources" / (slug + "w")
        wout.mkdir(parents=True, exist_ok=True)
        (wout / "chapters.json").write_text(json.dumps([entry(page, wiki, "p001", f"{wiki}网传版本", ws)], ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print(slug, len(secs), "节", "网传", len(ws), "则")


if __name__ == "__main__":
    main()
