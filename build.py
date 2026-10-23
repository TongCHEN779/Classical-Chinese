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


def build_juan(book, part, vol, src_path):
    pslug, ptitle, pord, nvol = part
    heading, entries = parse_juan(src_path)
    r = "../../"
    toc = "".join(f'<li><a href="#e{i}">{esc(e["title"])}</a></li>' for i, e in enumerate(entries, 1))
    body = f"""<header class="top">
{crumbs([("古文库", r + "index.html"), (book["title"], "../index.html"), (ptitle, None)])}
<h1>{esc(ptitle)}<small>{esc(pord)}</small></h1>
<h2>{esc(heading)}</h2>
<p class="hint">鼠标移到原文句子上，即显示白话；点击每则末尾的“注释”可展开补充说明。触屏设备请点按句子。</p>
</header>
<main>
<details class="toc" open><summary>本卷目录</summary><ol>{toc}</ol></details>
{chr(10).join(render_entry(i, e) for i, e in enumerate(entries, 1))}
<nav class="pager"><a href="../index.html">← 返回目录</a><span class="off">下一卷：待整理</span></nav>
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
        for f in sorted((SRC / book["slug"] / part[0]).glob("juan*.txt")) if (SRC / book["slug"] / part[0]).exists() else []:
            vol = int(f.stem[4:])
            done[(part[0], vol)] = build_juan(book, part, vol, f)
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


def build_home():
    cards = "".join(
        f'<li><a href="{b["slug"]}/index.html"><strong>{esc(b["title"])}</strong><span>{esc(b["author"])}</span><p>{esc(b["intro"])}</p></a></li>'
        for b in BOOKS
    )
    body = f"""<header class="top"><h1>古文库<small>原文在前，白话随手可得</small></h1></header>
<main><ul class="books">{cards}</ul></main>"""
    (ROOT / "index.html").write_text(page("古文库", body, ""), encoding="utf8")


if __name__ == "__main__":
    for b in BOOKS:
        build_book(b)
    build_home()
    print("done")
