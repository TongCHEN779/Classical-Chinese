#!/usr/bin/env python3
"""缓存维基文库《饮水词》（纳兰性德，131首）：写入 sources/yinshuici/chapters.json（一页，每首词为一节，每阕为一段）。

《饮水词》页面上的词大多没有标点，按行分句。标点取自维基文库《纳兰词全集》里同一首词（逐字对齐后移植，
两处文字有出入的字仍以《饮水词》页面为准）；对不上的词，标点由 sources/yinshuici/punct_manual.json 手工给出。
词前的小序/题（如“〈悼亡〉”）作为该节第一段（"verse_from" 为 1），其余各段为词的各阕。

  python3 tools/fetch_yinshuici.py
"""
import difflib
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sources/yinshuici"
PUNCT = "，。？！；：、"
APP = re.compile(r"(?:\（|\()?(?:一作|纳兰手迹作)“[^”]*”(?:\）|\))?")      # 底本的异文夹注，移到注释里
STRIP = re.compile(r"[，。？！；：、“”‘’（）()〈〉\s]")


def api(title):
    url = "https://zh.wikisource.org/w/api.php?format=json&formatversion=2&action=parse&prop=text|revid&variant=zh-hans&disableeditsection=1&page=" + urllib.parse.quote(title)
    for _ in range(4):
        out = subprocess.run(["curl", "-s", "-m", "90", url], capture_output=True, text=True).stdout
        try:
            return json.loads(out)["parse"]
        except Exception:
            pass
    raise RuntimeError(title)


def root_of(page):
    r = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    for x in r.select("table, .noprint, style, .licenseContainer"):
        x.decompose()
    return r


def stanzas_of(el):
    """<br> 换行：单个空行是行与行之间的换行，连续空行（两个以上）是阕与阕之间的分隔。"""
    for br in el.find_all("br"):
        br.replace_with("\n")
    text = el.get_text("")
    out = []
    for blk in re.split(r"\n\s*\n\s*\n", text.strip()):
        lines = [l.strip() for l in blk.split("\n") if l.strip()]
        if lines:
            out.append(lines)
    return out


def lines_of(el):
    for br in el.find_all("br"):
        br.replace_with("\n")
    return [l.strip() for l in el.get_text("").split("\n")]


def parse_ysc(page):
    poems, tune, sub = [], None, ""
    for el in root_of(page).children:
        if not getattr(el, "name", None):
            continue
        cls = el.get("class") or []
        if "mw-heading" in cls:
            tune = el.find(re.compile("h[1-6]")).get_text(strip=True)
            sub = ""
        elif el.name == "p":
            t = re.sub(r"\s+", "", el.get_text("", strip=True))
            if t.startswith("又"):
                sub = t[1:]
            elif t.startswith("〈"):
                sub = t
        elif "poem" in cls or "center" in cls:
            st = stanzas_of(el)
            variants = [m.group(0) for l in st for ln in l for m in APP.finditer(ln)]
            st = [[APP.sub("", ln) for ln in l] for l in st]
            if sum(ch in PUNCT for l in st for ln in l for ch in ln) <= 3:      # 个别零星标点不算自带标点
                st = [[re.sub("[" + PUNCT + "]", "", ln) for ln in l] for l in st]
            poems.append({"tune": tune, "sub": sub, "stanzas": st, "variants": variants})
            sub = ""
    return poems


def parse_full(page):
    out, cur = [], None
    for el in root_of(page).children:
        if not getattr(el, "name", None):
            continue
        cls = el.get("class") or []
        if "mw-heading" in cls:
            cur = el.get_text(strip=True)
        elif el.name == "p" or "poem" in cls:
            t = "".join(lines_of(el))
            if t:
                out.append(t)
    return out


def transfer(a, bfull):
    """a：无标点的字串；bfull：带标点的另一版本。返回 a 的各字后的标点（dict 下标→标点串）。"""
    bchars, bmark = [], {}
    for ch in bfull:
        if ch in PUNCT:
            bmark[len(bchars) - 1] = bmark.get(len(bchars) - 1, "") + ch
        elif not STRIP.fullmatch(ch):
            bchars.append(ch)
    b = "".join(bchars)
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    amap = {}
    for tag, i1, i2, j1, j2 in m.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                amap[j1 + k] = i1 + k
        elif tag == "replace":
            for k in range(j2 - j1):
                amap[j1 + k] = i2 - 1
        elif tag == "delete":
            pass
        # insert（b 里多出的字）：映射到前一个 a 字
        if tag in ("insert", "delete"):
            for k in range(j2 - j1):
                amap[j1 + k] = max(i1 - 1, 0)
    marks = {}
    for j, p in bmark.items():
        if j < 0:
            continue
        i = amap.get(j, len(a) - 1)
        marks[i] = marks.get(i, "") + p
    return marks, m.ratio()


def main():
    ysc = api("飲水詞")
    full = api("納蘭詞全集")
    poems = parse_ysc(ysc)
    fulls = parse_full(full)
    fkeys = [(STRIP.sub("", t), t) for t in fulls]
    manual = {}
    mp = OUT / "punct_manual.json"
    if mp.exists():
        manual = json.loads(mp.read_text(encoding="utf8"))
    sections, report = [], []
    for n, x in enumerate(poems):
        stanzas = ["".join(s) for s in x["stanzas"]]
        key = "".join(stanzas)
        if any(c in key for c in PUNCT):                 # 页面自带标点
            paras = stanzas
            how = "page"
        elif key in manual:
            paras = manual[key]
            assert STRIP.sub("", "".join(paras)) == key, key[:10]
            how = "manual"
        else:
            cands = [t for k, t in fkeys if key and (k == key or k.endswith(key) and len(k) - len(key) <= 6)]
            if not cands:
                cands = [max(fkeys, key=lambda z: difflib.SequenceMatcher(None, key, z[0]).ratio())[1]]
            marks, ratio = transfer(key, cands[0])
            how = "exact" if STRIP.sub("", cands[0]).endswith(key) else f"aligned{ratio:.2f}"
            paras, pos = [], 0
            for s in stanzas:
                txt = ""
                for k, ch in enumerate(s):
                    txt += ch + marks.get(pos + k, "")
                pos += len(s)
                if txt[-1] not in "。？！":
                    txt = txt.rstrip("，；、：") + "。"
                paras.append(txt)
        sub = re.sub(r"[〈〉()（）]", "", x["sub"]).strip() if x["sub"] else ""
        first = re.sub(r"[，。？！；：、]", "", paras[0])
        title = f"{x['tune']}（{first[:5]}…）" if len(first) > 5 else f"{x['tune']}（{first}）"
        title = re.sub(r"（([^）]*?)[，。]?…）", r"（\1…）", title)
        sec = {"title": title, "level": 3, "path": ["饮水词"], "author": "", "paragraphs": ([sub] if sub else []) + paras,
               "verse_from": 1 if sub else 0, "variants": x["variants"]}
        sections.append(sec)
        report.append((n, how, x["tune"], first[:8]))
    OUT.mkdir(parents=True, exist_ok=True)
    chapters = [{"slug": "p01", "title": "饮水词", "url": "https://zh.wikisource.org/zh-hans/" + urllib.parse.quote("飲水詞"),
                 "revision": str(ysc["revid"]), "heads": [], "sections": sections}]
    (OUT / "chapters.json").write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (OUT / "pages.json").write_text(json.dumps([["p01", "饮水词", None]], ensure_ascii=False) + "\n", encoding="utf8")
    for n, how, tune, first in report:
        if how not in ("exact", "page"):
            print(n, how, tune, first)
    print(len(sections), "首；其中对齐移植/手工：", sum(1 for r in report if r[1] not in ("exact", "page")))


if __name__ == "__main__":
    main()
