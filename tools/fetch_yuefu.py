#!/usr/bin/env python3
"""缓存维基文库《乐府诗集》一百卷（zh-hans），按“小节=一个三级/四级标题”拆开，写入 sources/yuefu/chapters.json。

  python3 tools/fetch_yuefu.py [缓存目录]      缓存目录默认 /tmp/yuefu_raw，缺的卷会从维基文库下载

小节规则：卷首序（第一个标题前的文字）、带正文的二级标题（曲名组序、整组诗）、每个三级标题、每个四级标题各成一节。
无标点的整行诗（div.poem，仅见卷一汉郊祀歌等）按联补“，。”，其余正文与维基文库逐字一致。
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_yutai import to_paragraphs

BASE = ROOT / "sources/yuefu"
CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/yuefu_raw")
CN = "零一二三四五六七八九"


def cn(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n - 10] if n > 10 else "")
    if n == 100:
        return "一百"
    t, u = divmod(n, 10)
    return CN[t] + "十" + (CN[u] if u else "")


CATS = [("郊庙歌辞", 12), ("燕射歌辞", 3), ("鼓吹曲辞", 5), ("横吹曲辞", 5), ("相和歌辞", 18), ("清商曲辞", 8), ("舞曲歌辞", 5),
        ("琴曲歌辞", 4), ("杂曲歌辞", 18), ("近代曲辞", 4), ("杂歌谣辞", 7), ("新乐府辞", 11)]


def category(n):
    for name, k in CATS:
        if n <= k:
            return name + cn(n)
        n -= k
    raise ValueError(n)


def load(n):
    f = CACHE / f"{n:03}.json"
    if not f.exists() or f.stat().st_size < 500:
        CACHE.mkdir(parents=True, exist_ok=True)
        u = "https://zh.wikisource.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "parse", "page": f"樂府詩集/{n:03}卷", "prop": "text|revid", "variant": "zh-hans",
             "disableeditsection": 1, "format": "json", "formatversion": 2})
        for a in range(6):
            try:
                time.sleep(1.5)
                req = urllib.request.Request(u, headers={"User-Agent": "ClassicalChineseBot/1.0 (personal study)"})
                data = urllib.request.urlopen(req, timeout=60).read()
                json.loads(data)
                f.write_bytes(data)
                break
            except Exception:
                time.sleep(4 * (a + 1))
        else:
            raise SystemExit(f"下载失败：卷{n}")
    return json.loads(f.read_text(encoding="utf8"))["parse"]


def text_of(el):
    for x in el.select("sup.reference, style, link, .noprint"):
        x.decompose()
    for br in el.find_all("br"):
        br.replace_with("\n")
    t = re.sub(r"\[\d+\]", "", el.get_text())
    return [re.sub(r"[ \t\r ]+$", "", l).strip() for l in t.split("\n")]


def parse_juan(n):
    page = load(n)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    secs, cur, h1, h2, h3 = [], None, "", "", ""

    def new(title, group, sub=""):
        nonlocal cur
        cur = {"title": title, "group": group, "parent": sub, "paragraphs": []}
        secs.append(cur)

    for el in root.find_all(["div", "p", "dl"], recursive=False):
        cls = el.get("class") or []
        if "mw-heading" in cls:
            lvl = int(re.search(r"mw-heading(\d)", " ".join(cls))[1])
            t = re.sub(r"\s+", " ", el.get_text()).strip()
            if lvl == 1:
                h1 = t
                continue
            if lvl == 2:
                h2, h3 = t, ""
                new(t, h2)       # 二级标题先建一节，若没有正文最后丢弃
                continue
            if lvl == 3:
                h3 = t
                new(t, h2)
            else:
                new(t, h2, h3)
            continue
        if el.name == "p":     # 个别卷（如卷五十八）把标题写成段落：【曲名】作者
            raw = "".join(l for l in text_of(el) if l)
            m = re.fullmatch(r"【([^】]+)】(.{0,14})", raw)
            if m:
                h3 = m[1] + (f"（{m[2].strip()}）" if m[2].strip() else "")
                new(h3, h2)
                continue
            if re.fullmatch(r"卷[^\s]{1,6}\s*[^\s]{2,8}", raw) and cur is None:
                continue
        if el.name == "div" and (cls and "poem" not in cls or el.get("id") == "headerContainer"):
            continue
        if el.name == "div" and not cls and not el.find("div", class_="poem") and not el.find("p"):
            continue
        if el.name == "dl":
            blocks = []
            for dd in el.find_all("dd") or [el]:
                blocks.append(("dd", " ".join(l for l in text_of(dd) if l)))
        elif el.name == "div":   # div.poem
            for x in el.select("style"):
                x.decompose()
            lines = [l for l in text_of(el) if l]
            blocks = [("poem", l) for l in to_paragraphs([{"kind": "lines", "lines": lines}])]
        else:
            blocks = [("p", "".join(l for l in text_of(el) if l))]
        for kind, t in blocks:
            t = re.sub(r"\s+", " ", t).strip() if kind == "dd" else t.strip()
            t = t.replace("", "")
            if not t or t.startswith(("主页面", "返回")):
                continue
            if cur is None:
                new("卷首序", "")
            if kind == "p" and "==" in t:     # 卷四、卷八各有一处二级标题的维基标记残留在上一段末尾：还原为标题
                t, head = t.split("==", 1)
                if t.strip():
                    cur["paragraphs"].append(t.strip())
                h2 = head.strip()
                new(h2, h2)
                continue
            cur["paragraphs"].append(t)
    secs = [s for s in secs if s["paragraphs"]]
    return h1, secs


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    out = []
    for n in range(1, 101):
        h1, secs = parse_juan(n)
        name = category(n)
        out.append({"slug": f"j{n:03}", "title": f"卷{cn(n)}", "name": name, "sections": secs})
        print(n, name, len(secs), sum(len(s["paragraphs"]) for s in secs), flush=True)
    (BASE / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
