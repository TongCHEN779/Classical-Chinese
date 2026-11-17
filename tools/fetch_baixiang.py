#!/usr/bin/env python3
"""白香词谱（舒梦兰选，维基文库《白香詞譜》）：取一百首词，去掉词谱的平仄标识（○●⊙△▲）、图例和〈叠句〉〈换平韵〉之类的格律小注，
每首一节（节名“一、菩萨蛮·闺情（李白）”），每阕一段；写入 sources/baixiangcipu/chapters.json，之后 prepare_texts.py 照常处理。
  python3 tools/fetch_baixiang.py
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

MARKS = re.compile(r"[○●⊙△▲◎◇◆]+")
SMALL = re.compile(r"〈[^〈〉]*〉")


def main():
    wiki = "白香詞譜"
    page = fetch(wiki, retries=8)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    secs = []
    for hd in root.select("div.mw-heading3"):
        h = hd.find("h3")
        small = h.find("small")
        author = re.sub(r"\s+", "", small.get_text("").strip("〈〉")) if small else ""
        author = re.sub(r"\s*（([^）]*)）", r"·\1", author)      # 作者名后的朝代等括注并入，免得节名里括号套括号
        if small:
            small.decompose()
        title = re.sub(r"\s*·\s*", "·", re.sub(r"\s+", " ", h.get_text("").strip()))
        poem = hd.find_next_sibling("div", class_="poem")
        assert poem is not None, title
        raw = str(poem).replace("<br/>\n", "<br/>").split("<br/>")
        lines = [BeautifulSoup(x, "html.parser").get_text("").replace("　", "").strip() for x in raw]
        paras, cur = [], []
        for l in lines:
            if not l:                       # 原文空行 = 阕与阕之间
                if cur:
                    paras.append("".join(cur)); cur = []
                continue
            l = MARKS.sub("", SMALL.sub("", l)).strip()
            if l:                           # 只剩平仄标识的行：丢掉，不断阕
                cur.append(l)
        if cur:
            paras.append("".join(cur))
        merged = paras
        secs.append({"title": f"{title}（{author}）" if author else title, "level": 3, "path": [], "author": author, "paragraphs": merged})
    out = ROOT / "sources/baixiangcipu"
    out.mkdir(parents=True, exist_ok=True)
    ch = [{"slug": "p01", "title": "白香词谱", "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
           "revision": str(page["revid"]), "heads": [], "sections": secs}]
    (out / "chapters.json").write_text(json.dumps(ch, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(len(secs), "首", sum(len(p) for s in secs for p in s["paragraphs"]), "字")
    for s in secs[:3] + secs[-2:]:
        print(s["title"], s["paragraphs"])


if __name__ == "__main__":
    main()
