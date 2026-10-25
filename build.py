#!/usr/bin/env python3
"""把 src/ 下的标注文本生成静态网页。用法：python3 build.py"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"

NUM = "零一二三四五六七八九十"


def cn(n):
    if n <= 10:
        return NUM[n]
    if n < 20:
        return "十" + NUM[n - 10]
    t, u = divmod(n, 10)
    return NUM[t] + "十" + (NUM[u] if u else "")


BOOKS = [
    {
        "slug": "rongzhai",
        "title": "容斋随笔",
        "author": "［宋］洪迈",
        "intro": "南宋洪迈所著的读书笔记，历时近四十年写成，分“五笔”，共七十四卷。"
                 "内容涉及经史、诗文、典制、考据、掌故，是宋代笔记中的名著。",
        "parts": [
            ("bi1", "容斋随笔", "第一笔", 16),
            ("bi2", "容斋续笔", "第二笔", 16),
            ("bi3", "容斋三笔", "第三笔", 16),
            ("bi4", "容斋四笔", "第四笔", 16),
            ("bi5", "容斋五笔", "第五笔", 10),
        ],
    }
]

CSS_LINK = '<link rel="stylesheet" href="{r}assets/style.css">'


def esc(s):
    return html.escape(s, quote=True)


GLOSS = re.compile(r"(（[^（）]*）|\([^()]*\))")


def orig_html(text):
    """原文中编者加的括注（年份、人名、注音）用淡色显示。"""
    parts = GLOSS.split(esc(text))
    return "".join(
        f'<span class="gl">{p}</span>' if i % 2 else p for i, p in enumerate(parts)
    )


def parse_juan(path):
    lines = path.read_text(encoding="utf8").splitlines()
    heading = lines[0].strip()
    entries = []
    cur = None
    for ln in lines[1:]:
        ln = ln.rstrip()
        if ln.startswith("# "):
            cur = {"title": ln[2:].strip(), "paras": [[]], "notes": []}
            entries.append(cur)
        elif not ln.strip():
            if cur and cur["paras"][-1]:
                cur["paras"].append([])
        elif ln.startswith("注："):
            cur["notes"].append(ln[2:].strip())
        elif "||" in ln:
            o, t = (x.strip() for x in ln.split("||", 1))
            cur["paras"][-1].append((o, t))
        else:
            raise ValueError(f"{path}: 无法解析：{ln}")
    for e in entries:
        e["paras"] = [p for p in e["paras"] if p]
    return heading, entries


def page(title, body, r, extra_js=False):
    js = f'<script src="{r}assets/reader.js" defer></script>' if extra_js else ""
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{CSS_LINK.format(r=r)}
{js}
</head>
<body>
{body}
</body>
</html>
"""


def crumbs(items):
    return '<nav class="crumbs">' + " › ".join(
        f'<a href="{h}">{esc(t)}</a>' if h else f"<span>{esc(t)}</span>" for t, h in items
    ) + "</nav>"


def render_entry(i, e):
    out = [f'<section class="entry" id="e{i}">', f'<h3><span class="no">{cn(i)}</span>{esc(e["title"])}</h3>']
    for para in e["paras"]:
        spans = "".join(
            f'<span class="s" tabindex="0" data-t="{esc(t)}">{orig_html(o)}</span>' for o, t in para
        )
        out.append(f"<p>{spans}</p>")
    if e["notes"]:
        items = "".join(f"<li>{esc(n)}</li>" for n in e["notes"])
        out.append(
            f'<button class="note-btn" type="button" aria-expanded="false" aria-controls="n{i}">'
            f'<span class="caret">▸</span> 注释（{len(e["notes"])}）</button>'
            f'<ol class="notes" id="n{i}" hidden>{items}</ol>'
        )
    out.append("</section>")
    return "\n".join(out)


def build_juan(book, part, vol, src_path, avail):
    pslug, ptitle, pord, nvol = part
    heading, entries = parse_juan(src_path)
    r = "../../"
    toc = "".join(f'<li><a href="#e{i}">{esc(e["title"])}</a></li>' for i, e in enumerate(entries, 1))
    prev_html = (f'<a href="juan{vol-1:02d}.html">← 卷{cn(vol-1)}</a>' if (vol - 1) in avail
                 else '<span class="off">&nbsp;</span>')
    next_html = (f'<a href="juan{vol+1:02d}.html">卷{cn(vol+1)} →</a>' if (vol + 1) in avail
                 else '<span class="off">下一卷：待整理</span>')
    body = f"""<header class="top">
{crumbs([("古文库", r + "index.html"), (book["title"], "../index.html"), (ptitle, None)])}
<h1>{esc(ptitle)}<small>{esc(pord)}</small></h1>
<h2>{esc(heading)}</h2>
<p class="hint">鼠标移到原文句子上，即显示白话；点击每则末尾的“注释”可展开补充说明。触屏设备请点按句子。</p>
</header>
<main>
<details class="toc" open><summary>本卷目录</summary><ol>{toc}</ol></details>
{chr(10).join(render_entry(i, e) for i, e in enumerate(entries, 1))}
<nav class="pager">{prev_html}<a href="../index.html">目录</a>{next_html}</nav>
</main>
<div id="tip" role="tooltip" hidden></div>
<footer>白话译文为辅助阅读的意译，如有出入，以原文为准。</footer>"""
    out = ROOT / book["slug"] / pslug / f"juan{vol:02d}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(f"{ptitle}·{heading.split('（')[0]}", body, r, True), encoding="utf8")
    return len(entries)


def build_book(book):
    done = {}
    for part in book["parts"]:
        d = SRC / book["slug"] / part[0]
        files = sorted(d.glob("juan*.txt")) if d.exists() else []
        avail = {int(f.stem[4:]) for f in files}
        for f in files:
            vol = int(f.stem[4:])
            done[(part[0], vol)] = build_juan(book, part, vol, f, avail)
    sections = []
    for pslug, ptitle, pord, nvol in book["parts"]:
        cells = []
        for v in range(1, nvol + 1):
            label = f"卷{cn(v)}"
            if (pslug, v) in done:
                cells.append(f'<li class="ok"><a href="{pslug}/juan{v:02d}.html">{label}<small>{done[(pslug, v)]}则</small></a></li>')
            else:
                cells.append(f'<li class="todo"><span>{label}<small>待整理</small></span></li>')
        sections.append(f'<section class="part"><h2>{esc(ptitle)}<small>{esc(pord)} · 共{nvol}卷</small></h2><ul class="vols">{"".join(cells)}</ul></section>')
    body = f"""<header class="top">
{crumbs([("古文库", "../index.html"), (book["title"], None)])}
<h1>{esc(book["title"])}<small>{esc(book["author"])}</small></h1>
<p class="intro">{esc(book["intro"])}</p>
</header>
<main>{"".join(sections)}</main>
<footer>已整理 {sum(done.values())} 则。</footer>"""
    out = ROOT / book["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(book["title"], body, "../"), encoding="utf8")


# ---------- 楚辞：按篇目成页，原文分节、逐节译文与注释 ----------
CHUCI_PAGES = [
    ("lisao", "离骚"), ("jiuge", "九歌"), ("tianwen", "天问"), ("jiuzhang", "九章"),
    ("yuanyou", "远游"), ("buju", "卜居"), ("yufu", "渔父"), ("jiubian", "九辩"),
    ("zhaohun", "招魂"), ("dazhao", "大招"), ("xishi", "惜誓"), ("zhaoyinshi", "招隐士"),
    ("qijian", "七谏"), ("aishiming", "哀时命"), ("jiuhuai", "九怀"), ("jiutan", "九叹"),
    ("jiusi", "九思"),
]
CHUCI_INTRO = ("战国楚人屈原及其后学的辞赋总集，由西汉刘向辑成，东汉王逸作注。"
               "此处依今人注译本整理：原文、注释、译文俱全。")

SHIJING_PAGES = [
    ("zhounan", "周南"), ("shaonan", "召南"), ("beifeng", "邶风"), ("yongfeng", "鄘风"),
    ("weifeng", "卫风"), ("wangfeng", "王风"), ("zhengfeng", "郑风"), ("qifeng", "齐风"),
    ("weifeng2", "魏风"), ("tangfeng", "唐风"), ("qinfeng", "秦风"), ("chenfeng", "陈风"),
    ("guifeng", "桧风"), ("caofeng", "曹风"), ("binfeng", "豳风"),
    ("xiaoya", "小雅"), ("daya", "大雅"), ("songzhou", "周颂"), ("lusong", "鲁颂"), ("shangsong", "商颂"),
]
GUWEN_PAGES = [
    ("juan01", "卷一·周文"), ("juan02", "卷二·周文"), ("juan03", "卷三·周文"), ("juan04", "卷四·战国文"),
    ("juan05", "卷五·秦汉文"), ("juan06", "卷六·汉文"), ("juan07", "卷七·六朝唐文"), ("juan08", "卷八·唐文"),
    ("juan09", "卷九·唐宋文"), ("juan10", "卷十·宋文"), ("juan11", "卷十一·宋文"), ("juan12", "卷十二·明文"),
]
POETRY = {
    "guwenguanzhi": {"title": "古文观止", "author": "［清］吴楚材、吴调侯 选编", "unit": "篇",
                     "intro": "清人选编的古文选本，自先秦至明代共二百二十二篇，分十二卷，为古文入门的经典读本。",
                     "pages": GUWEN_PAGES},
    "chuci": {"title": "楚辞", "author": "［战国］屈原等", "intro": CHUCI_INTRO, "pages": CHUCI_PAGES},
    "shijing": {"title": "诗经", "author": "［先秦］佚名",
                "intro": "中国最早的诗歌总集，分风、雅、颂三部分。国风收十五国风土歌谣一百六十首；小雅、大雅为朝廷宴飨、朝会之乐；颂为宗庙祭祀之乐。",
                "pages": SHIJING_PAGES},
}
CIRC = re.compile(r"([\u2460-\u2473\u3251-\u325f]+)")


def poem_orig(text):
    out = []
    for i, part in enumerate(CIRC.split(esc(text))):
        out.append(f"<sup>{part}</sup>" if i % 2 else part)
    return "".join(out).replace("/", "<br>")


def parse_poems(paths):
    sections = []
    cur = None
    for path in paths:
        for ln in path.read_text(encoding="utf8").splitlines():
            ln = ln.rstrip()
            if not ln.strip():
                continue
            if ln.startswith("# "):
                cur = {"title": ln[2:].strip(), "intro": [], "chunks": []}
                sections.append(cur)
            elif ln.startswith("题解："):
                cur["intro"].append(ln[3:].strip())
            elif ln.startswith("原："):
                o, t = (x.strip() for x in ln[2:].split("||", 1))
                cur["chunks"].append({"o": o, "t": t, "notes": []})
            elif ln.startswith("注："):
                cur["chunks"][-1]["notes"].append(ln[2:].strip())
            else:
                raise ValueError(f"{path}: 无法解析：{ln}")
    return sections


def build_poetry(bslug, spec):
    r = "../"
    base = SRC / bslug
    btitle = spec["title"]
    pages = []
    for slug, title in spec["pages"]:
        files = sorted((base / slug).glob("*.txt")) if (base / slug).exists() else []
        pages.append((slug, title, files))
    avail = [i for i, (_, _, f) in enumerate(pages) if f]
    cells, total = [], 0
    for i, (slug, title, files) in enumerate(pages):
        if not files:
            cells.append(f'<li class="todo"><span>{esc(title)}<small>待整理</small></span></li>')
            continue
        secs = parse_poems(files)
        nchunk = sum(len(s["chunks"]) for s in secs)
        total += nchunk
        cells.append(f'<li class="ok"><a href="{slug}.html">{esc(title)}<small>{len(secs)}{spec.get("unit", "节")}</small></a></li>')
        uid = 0
        body_secs = []
        for si, sec in enumerate(secs, 1):
            parts = [f'<section class="entry" id="e{si}">']
            multi = len(secs) > 1
            parts.append(f'<h3>{esc(sec["title"])}</h3>' if multi else "")
            if sec["intro"]:
                uid += 1
                items = "".join(f"<p>{esc(x)}</p>" for x in sec["intro"])
                parts.append(
                    f'<button class="note-btn" type="button" aria-expanded="false" aria-controls="n{uid}">'
                    f'<span class="caret">▸</span> 题解</button><div class="notes intro-box" id="n{uid}" hidden>{items}</div>')
            for ch in sec["chunks"]:
                parts.append(f'<p class="v"><span class="s" tabindex="0" data-t="{esc(ch["t"])}">{poem_orig(ch["o"])}</span></p>')
                if ch["notes"]:
                    uid += 1
                    li = "".join(f"<li>{esc(n)}</li>" for n in ch["notes"])
                    parts.append(
                        f'<button class="note-btn" type="button" aria-expanded="false" aria-controls="n{uid}">'
                        f'<span class="caret">▸</span> 注释（{len(ch["notes"])}）</button><ul class="notes plain" id="n{uid}" hidden>{li}</ul>')
            parts.append("</section>")
            body_secs.append("\n".join(x for x in parts if x))
        toc = ""
        if len(secs) > 1:
            toc = ('<details class="toc" open><summary>本篇目录</summary><ol>'
                   + "".join(f'<li><a href="#e{k}">{esc(s["title"])}</a></li>' for k, s in enumerate(secs, 1))
                   + "</ol></details>")
        prev_i = max([j for j in avail if j < i], default=None)
        next_i = min([j for j in avail if j > i], default=None)
        prev_h = (f'<a href="{pages[prev_i][0]}.html">← {esc(pages[prev_i][1])}</a>' if prev_i is not None
                  else '<span class="off">&nbsp;</span>')
        next_h = (f'<a href="{pages[next_i][0]}.html">{esc(pages[next_i][1])} →</a>' if next_i is not None
                  else '<span class="off">&nbsp;</span>')
        body = f"""<header class="top">
{crumbs([("古文库", r + "index.html"), (btitle, "index.html"), (title, None)])}
<h1>{esc(title)}<small>{esc(btitle)}</small></h1>
<p class="hint">鼠标移到原文上，即显示白话译文；点击“注释”“题解”可展开或收起。触屏设备请点按原文。</p>
</header>
<main>
{toc}
{chr(10).join(body_secs)}
<nav class="pager">{prev_h}<a href="index.html">目录</a>{next_h}</nav>
</main>
<div id="tip" role="tooltip" hidden></div>
<footer>原文依注译本转录；白话译文、注释、题解为编者自撰，仅供辅助阅读，以原文为准。</footer>"""
        out = ROOT / bslug / f"{slug}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(f"{title}·{btitle}", body, r, True), encoding="utf8")
    body = f"""<header class="top">
{crumbs([("古文库", "../index.html"), (btitle, None)])}
<h1>{esc(btitle)}<small>{esc(spec["author"])}</small></h1>
<p class="intro">{esc(spec["intro"])}</p>
</header>
<main><section class="part"><ul class="vols">{"".join(cells)}</ul></section></main>
<footer>已整理 {total} 节。</footer>"""
    (ROOT / bslug).mkdir(parents=True, exist_ok=True)
    (ROOT / bslug / "index.html").write_text(page(btitle, body, "../"), encoding="utf8")
    return total


def build_home():
    cards = "".join(
        f'<li><a href="{b["slug"]}/index.html"><strong>{esc(b["title"])}</strong><span>{esc(b["author"])}</span><p>{esc(b["intro"])}</p></a></li>'
        for b in BOOKS
    )
    for k, v in POETRY.items():
        cards += (f'<li><a href="{k}/index.html"><strong>{esc(v["title"])}</strong><span>{esc(v["author"])}</span>'
                  f'<p>{esc(v["intro"])}</p></a></li>')
    body = f"""<header class="top"><h1>古文库<small>原文在前，白话随手可得</small></h1></header>
<main><ul class="books">{cards}</ul></main>"""
    (ROOT / "index.html").write_text(page("古文库", body, ""), encoding="utf8")


if __name__ == "__main__":
    for b in BOOKS:
        build_book(b)
    for _k, _v in POETRY.items():
        build_poetry(_k, _v)
    build_home()
    print("done")
