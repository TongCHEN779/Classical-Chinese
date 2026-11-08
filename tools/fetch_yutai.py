#!/usr/bin/env python3
"""缓存维基文库《玉台新咏》（徐陵编）：以书名页目录为纲，序、十卷各首诗按目录顺序取各自单页正文，写入 sources/yutai/chapters.json。

  python3 tools/fetch_yutai.py [缓存目录]      # 缓存目录默认 /tmp/yutai_raw，可复用以免重复下载
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from catalog_zizhitongjian import API, get

BASE = ROOT / "sources/yutai"
CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/yutai_raw")
CN = "零一二三四五六七八九"


def cn(n):
    return "十" if n == 10 else CN[n]


# 目录链接指向消歧义页时，改取对应作者/篇章的具体页面
RESOLVE = {
    ("隴西行", "无名氏"): "隴西行_(天上何所有)", ("同聲歌", "张衡"): "同聲歌_(張衡)", ("擬古詩", "陶潜"): "擬古詩_(陶潛)",
    ("思歸", "范云"): "思歸_(范雲)", ("春怨", "王僧孺"): "春怨_(王僧孺)", ("相逢行", "张率"): "相逢行_(張率)",
    ("梅花落", "吴均"): "梅花落_(吳均)", ("臨高臺", "梁武帝"): "臨高臺_(蕭衍)", ("紫騮馬", "皇太子"): "紫騮馬_(蕭綱)",
    ("怨歌行", "简文帝"): "怨歌行_(蕭綱)", ("櫂歌行", "简文帝"): "櫂歌行_(蕭綱)", ("採桑", "简文帝"): "採桑_(蕭綱)",
    ("秋閨", "刘邈"): "秋閨_(劉邈)", ("秋思", "萧悫"): "秋思_(蕭慤)", ("閨情", "王筠"): "閨情_(王筠)",
    ("東飛伯勞歌", "无名氏"): "東飛伯勞歌_(蕭衍)", ("淥水曲", "江洪"): "淥水曲_(江洪)", ("秋風", "江洪"): "秋風(江洪)",
    ("春閨思", "萧子显"): "春閨思_(蕭子顯)", ("春遊", "谢朓"): "春遊_(謝朓)",
}


def api_parse(title):
    for attempt in range(5):
        try:
            time.sleep(1.1)
            j = json.loads(get(API, {"action": "parse", "page": title.replace("_", " "), "prop": "text|revid", "variant": "zh-hans",
                                     "redirects": 1, "disableeditsection": 1, "format": "json", "formatversion": 2}))
            if "parse" in j:
                return j["parse"]
            return None
        except Exception:
            time.sleep(3 * 2 ** attempt)
    return None


def cached(title):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (re.sub(r"[^0-9A-Za-z一-鿿]", "_", title) + ".json")
    if f.exists():
        d = json.loads(f.read_text(encoding="utf8"))
        d.setdefault("revision", d.get("revid", ""))
        return d
    p = api_parse(title)
    if p is None:
        return None
    d = {"title": title, "resolved": p["title"], "revision": str(p["revid"]), "html": p["text"]}
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf8")
    return d


def toc_entries():
    """按书名页目录顺序返回 [(卷标记, 作者, 链接标题, 显示名)]。每个 <li> 只取直接挂在它下面的第一个非作者链接
    （“(古诗十九首之五)”之类括注里的链接、作者链接不算）。"""
    d = cached("玉臺新詠")
    root = BeautifulSoup(d["html"], "html.parser").select_one(".mw-parser-output")
    out, vol, author = [], None, ""
    for node in root.descendants:
        if not isinstance(node, Tag):
            continue
        cls = node.get("class") or []
        if node.name == "div" and "mw-heading2" in cls:
            vol = node.get_text().strip()
            author = ""
        elif node.name == "li" and vol and vol != "注释":
            b = node.find("b", recursive=False)
            if b is not None:
                author = re.sub(r"\s+", "", b.get_text()).strip()
            elif node.find_parent(["li", "ol", "dd"]) is None:   # 顶层条目作者名未加粗时，取链接前的文字（如“繁钦　定情诗一首”）
                pre = ""
                for ch in node.children:
                    if isinstance(ch, Tag) and ch.name == "a":
                        break
                    if isinstance(ch, Tag) and ch.name in ("ul", "ol", "dl"):
                        break
                    pre += ch.get_text() if isinstance(ch, Tag) else str(ch)
                pre = re.sub(r"[\s\u3000]+", "", pre)
                if pre and not pre.startswith("又") and 2 <= len(pre) <= 8 and not re.search(r"[0-9()（）]", pre):
                    author = "无名氏" if pre == "无人名" else pre
            for a in node.find_all("a", recursive=False):
                href = a.get("href", "")
                if not href.startswith("/wiki/"):
                    continue
                t = unquote(href[6:])
                if t.startswith(("Author:", "Special:", "File:", "Portal:")) or "#" in t:
                    continue
                out.append((vol, author, t, a.get_text().strip()))
                break
    return out


def norm_author(a):
    if a in ("", "古诗八首", "古乐府诗六首", "古绝句") or a.endswith("首"):
        return "无名氏"
    return {"皇太子圣制": "皇太子"}.get(a, a)


def clean_lines(el):
    """把 div.poem / p 里以 <br> 分行的文字拆成行。"""
    for x in el.select("sup.reference, .variant-tooltip, style, link, small"):
        x.decompose()
    for br in el.find_all("br"):
        br.replace_with("\n")
    t = el.get_text()
    t = re.sub(r"\[\d+\]", "", t)
    return [re.sub(r"[ \t\r]+$", "", l.replace("\xa0", " ")).strip("\n") for l in t.split("\n")]


def parse_work(d):
    """一首（组）诗的单页：返回 [{"kind": "label"|"lines", "lines": [...]}]。"""
    root = BeautifulSoup(d["html"], "html.parser").select_one(".mw-parser-output")
    for x in root.select("table, .licenseContainer, ol.references, .reflist, hr, style, meta, link"):
        x.decompose()
    blocks = []

    def walk(el):
        for c in el.children:
            if not isinstance(c, Tag):
                continue
            cls = c.get("class") or []
            if c.name == "div" and "mw-heading" in cls:
                if c.get_text().strip() == "注释":
                    return True
                continue
            if c.name == "div" and "poem" in cls:
                blocks.append({"kind": "lines", "lines": [l for l in clean_lines(c) if l.strip()]})
            elif c.name == "dl":
                for dd in c.find_all("dd") or [c]:
                    for x in dd.select("sup.reference, .variant-tooltip, small, style, link"):
                        x.decompose()
                    t = re.sub(r"\[\d+\]", "", re.sub(r"[\s\u3000]+", "" if len(dd.get_text()) < 14 else " ", dd.get_text())).strip()
                    if not t or t.startswith(("主页面", "返回", "本作品")):
                        continue
                    if re.fullmatch(r"其[一二三四五六七八九十]+|.{0,10}[·．]之[一二三四五六七八九十]+|.{1,4}", t.replace(" ", "")):
                        blocks.append({"kind": "label", "lines": [t.replace(" ", "")]})
                    else:
                        blocks.append({"kind": "lines", "lines": [t]})
            elif c.name == "p":
                ls = [l for l in clean_lines(c) if l.strip()]
                if ls:
                    blocks.append({"kind": "lines", "lines": ls})
            elif c.name == "div" and not cls:
                continue        # 页首导航
            elif c.name in ("center", "div", "blockquote"):
                if walk(c):
                    return True
        return False

    walk(root)
    return blocks


FINAL = "。！？；"
FLAGS = []


def to_paragraphs(blocks):
    """原页面里的诗按联分行，行内两半以全角空格隔开且多数不带标点。整理者按联加标点：
    “甲　乙”→“甲，乙。”（已有句末标点的行原样保留）；不分半句的单句行两两合并为一联。"""
    out = []
    for b in blocks:
        if b["kind"] == "label":
            out.extend(b["lines"])
            continue
        pending = ""
        for line in b["lines"]:
            line = line.strip()
            if not line:
                continue
            if re.search("[%s]" % FINAL, line):
                if pending:
                    out.append(pending + "。")
                    pending = ""
                out.append(line)
                continue
            if len(line) >= 10 and not re.search(r"[\u3000 ，、]", line):
                n = 5 if len(line) % 5 == 0 else 7 if len(line) % 7 == 0 else 0
                if n:      # 整首（或整段）诗连写无标点：按五言/七言每句等长切开，两句一联
                    if pending:
                        out.append(pending + "。")
                        pending = ""
                    cl = [line[i:i + n] for i in range(0, len(line), n)]
                    for i in range(0, len(cl), 2):
                        out.append("，".join(cl[i:i + 2]) + "。")
                    FLAGS.append(("blob%d" % n + ("*" if len(line) % 35 == 0 else ""), line[:20]))
                    continue
                FLAGS.append(("odd", line[:20]))
            halves = [h for h in re.split(r"[\u3000 ]+", line) if h]
            if len(halves) >= 2:
                if pending:
                    out.append(pending + "。")
                    pending = ""
                out.append("，".join(halves) + "。")
            else:
                if pending:
                    out.append(pending + "，" + line + "。")
                    pending = ""
                else:
                    pending = line
        if pending:
            out.append(pending + "。")
    return out


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    entries = toc_entries()
    vols = ["序"] + [f"卷{cn(i)}" for i in range(1, 11)]
    chapters = {v: [] for v in vols}
    for vol, author, t, name in entries:
        if vol not in chapters:
            continue
        chapters[vol].append((author, t, name))
    result = []
    for vi, vol in enumerate(vols):
        slug = "xu" if vol == "序" else f"j{vi:02}"
        secs = []
        if vol == "序":
            d = cached("玉臺新詠/序")
            root = BeautifulSoup(d["html"], "html.parser").select_one(".mw-parser-output")
            paras = []
            for p in root.find_all("p", recursive=False):
                for x in p.select("sup.reference"):
                    x.decompose()
                tx = re.sub(r"\s+", "", p.get_text())
                if tx:
                    paras.append(tx)
            secs.append({"title": "玉台新咏序", "author": "徐陵", "url": "https://zh.wikisource.org/zh-hans/" + quote("玉臺新詠/序"),
                         "revision": d["revision"], "blocks": [{"kind": "lines", "lines": [x]} for x in paras]})
        else:
            for author, t, name in chapters[vol]:
                t = RESOLVE.get((t, norm_author(author)), t)
                d = cached(t)
                if d is None:
                    print("MISSING", t, flush=True)
                    continue
                secs.append({"title": name, "author": norm_author(author), "page": t, "url": "https://zh.wikisource.org/zh-hans/" + quote(t),
                             "revision": d["revision"], "blocks": parse_work(d)})
                print(slug, name, author, len(secs[-1]["blocks"]), flush=True)
        for sec in secs:
            sec["paragraphs"] = to_paragraphs(sec.pop("blocks"))
        result.append({"slug": slug, "title": vol, "sections": secs})
    (BASE / "chapters.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
