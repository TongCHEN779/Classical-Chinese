#!/usr/bin/env python3
"""把《徐霞客游记》各日记页重新分节：严格一天一节（不合并相邻日期）；并把已写好的白话、注释按段落迁移到新分节上。

  python3 tools/resection_xuxiake.py            # 抓取、核对、写 chapters.json、迁移注释
日期来源：有日期标题的页，以“日”标题为一天；无标题的页，以段首“日期＋两个全角空格”为一天。
节名＝带月份的日期（上下文取最近的“X月”）；“（公元…年）”之类括注不进节名。
"""
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch
from fetch_texts import clean
import prepare_texts as pt

BASE = ROOT / "sources/xuxiake"
MONTH = re.compile(r"[正闰]?[二三四五六七八九十一腊冬]+月|正月|闰[二三四五六七八九十一]+月")
SCRATCH = Path("/private/tmp/claude-501/-Users-tchen-Documents-Github-Classical-Chinese/e7466f21-deea-4725-bfa8-4524014c6ed4/scratchpad/xx_old_ann")


def walk(root):
    """产出 ('h', 级别, 文本) 或 ('p', 清洗后文本, 段首日期组或 None)。"""
    for x in root.select("table, .licenseContainer, ol.references, style, meta, link, #headerContainer, .hatnote, ul#toc"):
        x.decompose()
    for x in root.select("div.prose, div.poem, dl"):
        x.unwrap()
    for el in root.find_all(["div", "p"], recursive=False):
        cls = el.get("class") or []
        if "mw-heading" in cls:
            h = el.find(re.compile("h[1-6]"))
            yield "h", int(h.name[1]), clean(h)
        elif el.name == "p":
            raw = el.get_text()
            t = clean(el)
            if not t:
                continue
            m = re.match(r"^([^　\n]{1,45}?)　　", raw)
            day = m.group(1) if m and (re.search(r"[日晦朔]$", m.group(1)) or "日" in m.group(1)) else None
            yield "p", t, day
        elif el.name == "div":
            for p in el.find_all(["p", "dd", "li"]):
                t = clean(p)
                if t:
                    yield "p", t, None


def day_title(label, ctx):
    label = re.sub(r"[（(][^）)]*[）)]", "", label).strip()
    m = MONTH.search(label)
    if m:
        ctx["month"] = m.group(0)
        return label
    return (ctx["month"] + label) if ctx["month"] else label


# 少数页（滇游日记九、十三）没有日期标题，段首也没有全角空格，日期直接接在正文前（或单独成段）
DAY_PREFIX = re.compile(r"^((?:[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])?(?:闰?[正二三四五六七八九十]+月)?(?:初[一二三四五六七八九十]|二十[一二三四五六七八九]?|三十|十[一二三四五六七八九]?|[二三四五六七八九]日)日?)")


def build_sections(items, page_title):
    ctx = {"month": ""}
    secs, cur, headed = [], None, any(k == "h" for k, *_ in items)
    if not headed and not any(it[2] for it in items if it[0] == "p"):
        items = [(k, t, (m.group(1) if (m := DAY_PREFIX.match(t)) and m.group(1).endswith("日") else None)) if k == "p" else (k, t, None) for k, t, *_ in items] if False else [
            ("p", it[1], (m.group(1) if (m := DAY_PREFIX.match(it[1])) and m.group(1).endswith("日") else None)) if it[0] == "p" else it for it in items]
    for it in items:
        if it[0] == "h":
            if it[1] == 1 and not re.search(r"日|晦|朔", it[2]):   # 年份标题（如“癸丑”）
                continue
            label = it[2]
            m = MONTH.search(label)
            if m and not re.search(r"[日晦朔]", label):          # 月份标题：只更新上下文
                ctx["month"] = m.group(0)
                continue
            cur = {"title": day_title(label, ctx), "level": 3, "path": [page_title], "author": "", "paragraphs": []}
            secs.append(cur)
        else:
            _, text, day = it
            if not headed and day:
                cur = {"title": day_title(day, ctx), "level": 3, "path": [page_title], "author": "", "paragraphs": []}
                secs.append(cur)
            if cur is None:
                cur = {"title": "开篇", "level": 3, "path": [page_title], "author": "", "paragraphs": []}
                secs.append(cur)
            cur["paragraphs"].append(text)
    return [s for s in secs if s["paragraphs"]]


def main():
    only = set(sys.argv[1:])
    data = json.loads((BASE / "chapters.json").read_text(encoding="utf8"))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    report = []
    for ch in data:
        if "日记" not in ch["title"] or (only and ch["slug"] not in only):
            continue
        page = fetch(unquote(ch["url"].split("zh-hans/")[1]))
        root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
        new = build_sections(list(walk(root)), ch["title"])
        old_paras = [p for s in ch["sections"] for p in s["paragraphs"]]
        new_paras = [p for s in new for p in s["paragraphs"]]
        assert new_paras == old_paras, (ch["slug"], len(new_paras), len(old_paras))
        # 迁移注释：旧分节的各段（译、注）按段落顺序拉平，再按新分节切开
        old_draft = pt.load_draft("xuxiake", ch["slug"], len(ch["sections"]))
        flat = []
        for s, item in zip(ch["sections"], old_draft):
            segs = (item or {}).get("段落", [])
            assert len(segs) == len(s["paragraphs"]), (ch["slug"], s["title"], len(segs), len(s["paragraphs"]))
            flat.extend(segs)
        items, k = [], 0
        for s in new:
            n = len(s["paragraphs"])
            items.append({"题解": "", "段落": flat[k:k + n]})
            k += n
        assert k == len(flat)
        files = sorted((BASE / "annotations").glob(f"{ch['slug']}__*.json"))
        for f in files:
            shutil.copy(f, SCRATCH / f.name)
            f.unlink()
        (BASE / "annotations" / f"{ch['slug']}__0.json").write_text(
            json.dumps({"start": 0, "items": items}, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        report.append((ch["slug"], ch["title"], len(ch["sections"]), len(new)))
        ch["sections"] = new
        print(ch["slug"], ch["title"], len(report[-1:]) and f"{report[-1][2]} -> {len(new)} 节", flush=True)
    (BASE / "chapters.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("日记页", len(report), "共", sum(r[3] for r in report), "天")


if __name__ == "__main__":
    main()
