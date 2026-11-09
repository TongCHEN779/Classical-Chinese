#!/usr/bin/env python3
"""缓存维基文库的几部较长的笔记游记（扬州画舫录、陶庵梦忆、帝京景物略、都城纪胜、梦粱录、徐霞客游记），
写入 sources/<slug>/chapters.json（格式同 tools/fetch_texts.py）。

  python3 tools/fetch_books2.py [slug ...]

分节：每个标题（及其下正文）是一个单元；单元超过 G 字时按段落贪心切成若干节（不切断段落），
节名为“标题·首段开头”；游记按日期标题的相邻小单元合并成一节（节名“月·初一日至初五日”）。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch
from fetch_texts import items, lead

CN = "零一二三四五六七八九十"


def num(n):
    return CN[n] if n <= 10 else "十" + (CN[n - 10] if n > 10 and n < 20 else "") if n < 20 else CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")


BOOKS = {
    "huafanglu": {"wiki": "揚州畫舫錄", "g": 1800, "pages": (
        [("x1", "袁枚序", "揚州畫舫錄/袁枚序"), ("x2", "阮元序", "揚州畫舫錄/阮元序"), ("x3", "自序", "揚州畫舫錄/自序")]
        + [(f"j{n:02}", f"卷{num(n)}", f"揚州畫舫錄/{n:02}") for n in range(1, 19)])},
    "taoan": {"wiki": "陶庵夢憶", "g": 3000, "pages": (
        [("x1", "梦忆序", "陶庵夢憶/夢憶序"), ("x2", "陶庵梦忆序", "陶庵夢憶/陶庵夢憶序")]
        + [(f"j{n}", f"卷{num(n)}", f"陶庵夢憶/卷{n:02}") for n in range(1, 9)]
        + [("j9", "补", "陶庵夢憶/陶庵夢憶補"), ("x3", "伍跋", "陶庵夢憶/伍跋")])},
    "dijing": {"wiki": "帝京景物略", "g": 2500, "poem": True, "pages": (
        [("x0", "序与略例", "帝京景物略/0")] + [(f"j{n}", f"卷{num(n)}", f"帝京景物略/{n}") for n in range(1, 9)])},
    "ducheng": {"wiki": "都城紀勝", "g": 2500, "pages": [("p01", "都城纪胜", "都城紀勝")]},
    "mengliang": {"wiki": "夢粱錄", "g": 2500, "pages": (
        [("x1", "序", "夢粱錄/序")] + [(f"j{n:02}", f"卷{num(n)}", f"夢粱錄/卷{n:02}") for n in range(1, 21)])},
    "shanhaijing": {"wiki": "山海經", "g": 2200, "pages": (
        [("x1", "郭璞序", "山海經/郭璞序")]
        + [(f"j{i}", t, f"山海經/{w}") for i, (t, w) in enumerate([
            ("南山经", "南山經"), ("西山经", "西山經"), ("北山经", "北山經"), ("东山经", "東山經"), ("中山经", "中山經"),
            ("海外南经", "海外南經"), ("海外西经", "海外西經"), ("海外北经", "海外北經"), ("海外东经", "海外東經"),
            ("海内南经", "海內南經"), ("海内西经", "海內西經"), ("海内北经", "海內北經"), ("海内东经", "海內東經"),
            ("大荒东经", "大荒東經"), ("大荒南经", "大荒南經"), ("大荒西经", "大荒西經"), ("大荒北经", "大荒北經"),
            ("海内经", "海內經")], 1)])},
    "jinbenzhushu": {"wiki": "今本竹書紀年", "g": 2200, "year": True, "pages": [
        ("j1", "五帝纪", "今本竹書紀年/五帝紀"), ("j2", "夏纪", "今本竹書紀年/夏紀"), ("j3", "殷纪", "今本竹書紀年/殷紀"),
        ("j4", "周纪", "今本竹書紀年/周紀"), ("j5", "晋纪", "今本竹書紀年/晉紀"), ("j6", "魏纪", "今本竹書紀年/魏紀")]},
    "mutianzi": {"wiki": "穆天子傳", "g": 2200, "pages": (
        [("x1", "序一", "穆天子傳/序一"), ("x2", "序二", "穆天子傳/序二")]
        + [(f"j{n}", f"卷{num(n)}", f"穆天子傳/卷{'一二三四五六'[n - 1]}") for n in range(1, 7)])},
    "yandanzi": {"wiki": "燕丹子", "g": 2000, "pages": [("p01", "燕丹子", "燕丹子", "headings")]},
    "diwangshiji": {"wiki": "帝王世紀", "g": 2200, "titles_from_main": True, "pages": [(f"j{n}", f"帝王世纪第{CN[n]}", f"帝王世紀/第{CN[n]}") for n in range(1, 10)]},
    "yuejueshu": {"wiki": "越絕書", "g": 10**7, "pages": [(f"j{n:02}", f"卷{num(n)}", f"越絕書/卷{num(n).replace('零', '')}") for n in range(1, 16)]},
    "chunqiufanlu": {"wiki": "春秋繁露", "g": 10**7, "lines": True, "pages": [(f"j{n:02}", f"卷{num(n)}", f"春秋繁露/卷{n:02}") for n in range(1, 18)]},
    "wuyuechunqiu": {"wiki": "吳越春秋", "g": 10**7, "pages": [
        ("j01", "吴太伯传第一", "吳越春秋/吳太伯傳"), ("j02", "吴王寿梦传第二", "吳越春秋/吳王壽夢傳"), ("j03", "王僚使公子光传第三", "吳越春秋/王僚使公子光傳"),
        ("j04", "阖闾内传第四", "吳越春秋/闔閭內傳"), ("j05", "夫差内传第五", "吳越春秋/夫差內傳"), ("j06", "越王无余外传第六", "吳越春秋/越王無余外傳"),
        ("j07", "勾践入臣外传第七", "吳越春秋/勾踐入臣外傳"), ("j08", "勾践归国外传第八", "吳越春秋/勾踐歸國外傳"), ("j09", "勾践阴谋外传第九", "吳越春秋/勾踐陰謀外傳"),
        ("j10", "勾践伐吴外传第十", "吳越春秋/勾踐伐吳外傳"), ("x1", "佚文", "吳越春秋/佚文")]},
    "youyangzazu": {"wiki": "酉陽雜俎", "g": 10**7, "pages": (
        [("x1", "序", "酉陽雜俎/酉陽雜俎序")] + [(f"j{n:02}", f"卷{num(n)}", f"酉陽雜俎/卷{num(n)}") for n in range(1, 21)]
        + [(f"s{n:02}", f"续集卷{num(n)}", f"酉陽雜俎/續集/卷{num(n)}") for n in range(1, 11)])},
    "wenxindiaolong": {"wiki": "文心雕龍", "g": 1800, "pages": "MAIN_LI"},
    "guanzi": {"wiki": "管子", "g": 2200, "pages": "GUANZI"},
    "liexianzhuan": {"wiki": "列仙傳", "g": 10**7, "pages": [("p01", "列仙传", "列仙傳")]},
    "xuxiake": {"wiki": "徐霞客遊記", "g": 1800, "merge": True, "pages": "AUTO"},
}


def items_lines(root):
    """春秋繁露：全文在一个 div.prose 里，以换行分隔；无全角空格开头、以“第…”结尾的行是篇题，其余行是段落。"""
    d = root.select_one("div.prose")
    for x in d.select("table, .noprint"):
        x.decompose()
    started = False
    for ln in d.get_text("\n").split("\n"):
        raw = ln.strip("\r")
        t = re.sub(r"\s+", " ", raw).replace("\u3000", "").strip()
        if not t or re.search(r"[◀▶]|^目录$|^全书始$|^全书终$|^春秋繁露$|^卷第[一二三四五六七八九十]+$", t):
            continue
        if not raw.startswith("\u3000") and re.search(r"第[一二三四五六七八九十百零]+$", t):
            started = True
            yield 2, t
        elif started:
            yield 0, re.sub(r"〈[^〈〉]*〉", "", t)


def units(seq, poem=False, year=False):
    """seq 为 items() 的输出，返回 [(标题, 上级标题, 段落列表)]。"""
    out, trail, cur = [], [], None
    for lvl, t in seq:
        if lvl:
            if poem and "【" in t and cur is not None:
                cur[2].append(t)        # 诗题并入正文，作为该诗的首行
                continue
            if year and cur is not None and re.fullmatch(r"[元一二三四五六七八九十百零〇]+年", t):
                cur[2].append(t)        # 纪年标题（元年、二年…）并入所属帝王一节，作为该年记事的首行
                continue
            while trail and trail[-1][0] >= lvl:
                trail.pop()
            parent = trail[-1][1] if trail else ""
            trail.append((lvl, t))
            cur = (t, parent, [])
            out.append(cur)
        else:
            if cur is None:
                cur = ("", "", [])
                out.append(cur)
            cur[2].append(t)
    return [u for u in out if u[2]]


def sections(us, page_title, g, merge):
    if not us:
        return []
    secs = []
    # 1. 切分超长单元
    pieces = []
    for title, parent, paras in us:
        groups, cur, size = [], [], 0
        for p in paras:
            if cur and size + len(p) > g:
                groups.append(cur)
                cur, size = [], 0
            cur.append(p)
            size += len(p)
        if cur:
            groups.append(cur)
        for k, grp in enumerate(groups):
            name = title or page_title
            if len(groups) > 1 or not title:
                name = (title + "·" if title else "") + lead(grp[0])
            pieces.append({"title": name, "parent": parent, "head": title, "paragraphs": grp})
    # 2. 游记：合并相邻的小单元
    if merge:
        merged = []
        for p in pieces:
            size = sum(len(x) for x in p["paragraphs"])
            if (merged and merged[-1]["size"] + size <= g and merged[-1]["parent"] == p["parent"]
                    and p["head"] and merged[-1]["head"] and "·" not in p["title"] and "·" not in merged[-1]["title"]):
                m = merged[-1]
                m["paragraphs"] += p["paragraphs"]
                m["size"] += size
                m["last"] = p["head"]
            else:
                merged.append({**p, "size": size, "first": p["head"], "last": p["head"]})
        pieces = []
        for m in merged:
            if m.get("first") and m["first"] != m["last"]:
                name = f'{m["first"]}至{m["last"]}'
            else:
                name = m["title"]
            if m["parent"] and m["parent"] not in name and m.get("head") and "·" not in name:
                name = f'{m["parent"]}·{name}'
            pieces.append({"title": name, "paragraphs": m["paragraphs"]})
    return [{"title": p["title"], "level": 3, "path": [page_title], "author": "", "paragraphs": p["paragraphs"]} for p in pieces]


def main():
    want = set(sys.argv[1:])
    for slug, cfg in BOOKS.items():
        if want and slug not in want:
            continue
        pages = cfg["pages"]
        if pages == "AUTO":
            main_page = fetch(cfg["wiki"])
            soup = BeautifulSoup(main_page["text"], "html.parser")
            pages = []
            for i, a in enumerate(soup.select(".mw-parser-output ul li a"), 1):
                href = unquote(a.get("href", ""))
                if cfg["wiki"] in href and "/wiki/" in href:
                    wt = href.split("/wiki/", 1)[1].replace("_", " ")
                    pages.append((f"p{len(pages) + 1:02}", a.get_text().strip(), wt))
        elif pages == "MAIN_LI":      # 文心雕龙：目录页每个 li 一篇
            soup = BeautifulSoup(fetch(cfg["wiki"])["text"], "html.parser")
            pages = []
            for li in soup.select(".mw-parser-output li"):
                a = li.select_one("a")
                href = unquote(a.get("href", "")) if a else ""
                if href.startswith("/wiki/" + cfg["wiki"] + "/"):
                    pages.append((f"p{len(pages) + 1:02}", li.get_text().strip(), href[6:]))
        elif pages == "GUANZI":       # 管子：取“第NN篇”页；七法用总页（其下三个子页是另一版本），势为重定向页的目标
            soup = BeautifulSoup(fetch(cfg["wiki"])["text"], "html.parser")
            pages = []
            for a in soup.select(".mw-parser-output li a"):
                href = unquote(a.get("href", ""))
                m = re.match(r"/wiki/管子/第(\d+)篇(.+)$", href)
                if m:
                    wt = "管子/" + m.group(2) if m.group(1) == "42" else href[6:]
                    pages.append((f"p{m.group(1)}", a.get_text().strip() + "第" + num(int(m.group(1))), wt))
                elif href == "/wiki/管子/七法":
                    pages.append(("p06", "七法第六", "管子/七法"))
            pages.sort(key=lambda x: x[0])
        out = []
        for pslug, ptitle, wiki, *_ in pages:
            try:
                page = fetch(wiki)
            except Exception as e:            # 页面不存在（目录里的红链）等
                print("SKIP", slug, pslug, ptitle, wiki, type(e).__name__, flush=True)
                continue
            root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
            seq = list(items_lines(root)) if cfg.get("lines") else list(items(root))
            secs = sections(units(seq, cfg.get("poem", False), cfg.get("year", False)), ptitle, cfg["g"], cfg.get("merge", False))
            out.append({"slug": pslug, "title": ptitle, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
                        "revision": str(page["revid"]), "heads": [], "sections": secs})
            print(slug, pslug, ptitle, len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
