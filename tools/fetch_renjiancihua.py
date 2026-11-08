#!/usr/bin/env python3
"""缓存维基文库《人间词话》汇本（zh-hans）：正文与原页面自带的①②…注释，写入 sources/renjiancihua/chapters.json。

  python3 tools/fetch_renjiancihua.py [已下载的 parse JSON]      省略则从维基文库下载

结构：二级标题=页（卷上 / 卷下 / 附录），三级标题=一则；正文段落与“①　…”注释段落分开存放，注释挂在它前面最近的正文段落上。
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "sources/renjiancihua"
TITLE = "人間詞話"
NOTE = re.compile(r"^\s*[①-⑳]")
SLUGS = ["shang", "xia", "buyi"]


def load():
    if len(sys.argv) > 1:
        return json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))["parse"]
    u = "https://zh.wikisource.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "parse", "page": TITLE, "prop": "text|revid", "variant": "zh-hans", "disableeditsection": 1,
         "format": "json", "formatversion": 2})
    req = urllib.request.Request(u, headers={"User-Agent": "ClassicalChineseBot/1.0 (personal study)"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["parse"]


def clean(el):
    for x in el.select("sup.reference, style, link, .noprint"):
        x.decompose()
    t = el.get_text().replace("\xa0", " ")
    t = re.sub(r"\[\d+\]", "", t)
    return re.sub(r"[ \t\r\n]+", " ", t).strip()


def main():
    page = load()
    html = page["text"]
    root = BeautifulSoup(html if isinstance(html, str) else html["*"], "html.parser").select_one(".mw-parser-output")
    pages, cur_page, cur = [], None, None
    for el in root.find_all(["div", "p"], recursive=False):
        cls = el.get("class") or []
        if "mw-heading" in cls:
            lvl = int(re.search(r"mw-heading(\d)", " ".join(cls))[1])
            t = re.sub(r"\[编辑\]$", "", clean(el))
            if lvl == 2:
                cur_page = {"slug": SLUGS[len(pages)], "title": t, "sections": []}
                pages.append(cur_page)
                cur = None
            else:
                cur = {"title": t, "paragraphs": []}
                cur_page["sections"].append(cur)
            continue
        if el.name != "p" or cur is None:
            continue
        t = clean(el)
        if not t:
            continue
        if NOTE.match(t):
            assert cur["paragraphs"], ("注释前没有正文", cur["title"])
            cur["paragraphs"][cur.get("note_for", len(cur["paragraphs"]) - 1)]["notes"].append(t)
            cur["note_for"] = cur.get("note_for", len(cur["paragraphs"]) - 1)
        elif "note_for" in cur:      # 卷上五八：①注之后维基文库又附了两条无编号的注（“小玉：”“双成：”），仍属注释
            cur["paragraphs"][cur["note_for"]]["notes"].append(t)
        else:
            cur["paragraphs"].append({"text": t, "notes": []})
    for p in pages:
        for sec in p["sections"]:
            sec.pop("note_for", None)
    data = {"title": "人间词话", "author": "王国维", "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote(TITLE),
            "revision": str(page["revid"]), "pages": pages}
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "chapters.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    for p in pages:
        paras = [q for s in p["sections"] for q in s["paragraphs"]]
        print(p["slug"], p["title"], len(p["sections"]), "则", len(paras), "段", sum(len(q["notes"]) for q in paras), "条注")


if __name__ == "__main__":
    main()
