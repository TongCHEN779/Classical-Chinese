#!/usr/bin/env python3
"""把 src/ 下的标注文本生成静态网页。用法：python3 build.py"""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
SRC = ROOT / "src"

NUM = "零一二三四五六七八九十"


def cn(n):
    if n >= 100:
        h, r = divmod(n, 100)
        if r == 0:
            return NUM[h] + "百"
        if r < 10:
            return NUM[h] + "百零" + NUM[r]
        t, u = divmod(r, 10)
        return NUM[h] + "百" + NUM[t] + "十" + (NUM[u] if u else "")
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
        "intro": "",
        "parts": [
            ("xu", "容斋随笔序", "洪迈《随笔》刻本序", 1, "序"),
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

SENT = re.compile(r"[^。！？；]*[。！？；]+(?:[”’」』）]*[。！？；]+)*[”’」』）]*|[^。！？；]+$")


def split_sents(s):
    parts = [x for x in SENT.findall(s) if x.strip()]
    # A trailing editorial bracket closes the preceding sentence.
    if len(parts) > 1 and parts[-1].strip() == "〉":
        closing = parts.pop()
        parts[-1] += closing
    return parts


NOTE_HEAD = re.compile(r'[^。！？；：:\n]{1,64}：')
NOTE_QUOTED_HEAD = re.compile(r'“[^”\n]{1,32}”(?:即|指|为|是|同|通|见|出自)')
NOTE_CONTINUATION = re.compile(
    r'(?:的意思是|的看法是|的观点|的立意|'
    r'来对比|借此议论|用几个例子说明|指出.*|最意外的是.*|典出.*|见《.*)$'
)


def split_notes(text):
    """拆开合写的独立词条；引文、括注和同一词条的后续解释保持完整。"""
    stack = []
    opening = {'“': '”', '‘': '’', '「': '」', '『': '』',
               '（': '）', '(': ')', '《': '》', '〈': '〉'}
    starts = [0]
    for i, char in enumerate(text):
        if not stack and i:
            # 允许句末引号后的新词条，但不在尚未结束的引用中拆分。
            before = text[:i].rstrip('”’」』）)》〉 ')
            if before and before[-1] in '。！？；':
                head = NOTE_HEAD.match(text, i)
                quoted = NOTE_QUOTED_HEAD.match(text, i)
                citation = (head and head[0][:-1].endswith(('曰', '云', '载', '爻辞', '象辞'))
                            and text[head.end():].startswith(('“', '‘', '「', '『')))
                if ((head and all(head[0].count(a) == head[0].count(b)
                                  for a, b in opening.items())
                     and not citation
                     and not NOTE_CONTINUATION.search(head[0][:-1])) or quoted):
                    starts.append(i)
        if char in opening:
            stack.append(opening[char])
        elif stack and char == stack[-1]:
            stack.pop()
    starts.append(len(text))
    return [text[a:b].strip() for a, b in zip(starts, starts[1:]) if text[a:b].strip()]


def _frag_groups(raw):
    """把只剩标点、或以逗号等起首的碎句并回上一句（如夹注括号后单独的“。”）。"""
    groups = []
    for k, x in enumerate(raw):
        if groups and (not re.search(r"[\u4e00-\u9fff]", x) or x.lstrip()[:1] in "，；：、）〉"):
            groups[-1].append(k)
        else:
            groups.append([k])
    return groups


def split_pairs(o, t):
    """按句号/叹号/问号/分号把一段原文拆成句，并与译文逐句对应。
    译文里可用「¦」显式分句；句数对不上时整段不拆；碎句并回上一句。"""
    raw = split_sents(o)
    if len(raw) > 1:
        st = t.split("¦") if "¦" in t else split_sents(t)
        groups = _frag_groups(raw)
        if len(st) == len(raw):
            if "¦" in t:
                # 显式配译保留有正文的句子，即使底本在句首多了逗号。
                # 只有纯标点碎片仍需并回上一句。
                groups = []
                for k, x in enumerate(raw):
                    # 扩展区汉字也有正文意义，不能把单字句当作纯标点。
                    if groups and not any(char.isalnum() for char in x):
                        groups[-1].append(k)
                    else:
                        groups.append([k])
            return [("".join(raw[k] for k in g), "".join(st[k] for k in g)) for g in groups]
        if len(st) == len(groups):
            return [("".join(raw[k] for k in g), x) for g, x in zip(groups, st)]
    return [(o, t.replace("¦", ""))]


def has_sentence_pairs(chunk):
    """Recognize explicit, nonempty glosses aligned with each original sentence."""
    original = split_sents(chunk["o"])
    modern = chunk["t"].split("¦")
    return (len(original) == len(modern) and all(t.strip() for t in modern)
            and [o for o, _ in split_pairs(chunk["o"], chunk["t"])] == original)


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
            cur["notes"].extend(split_notes(ln[2:].strip()))
        elif "||" in ln:
            o, t = (x.strip() for x in ln.split("||", 1))
            cur["paras"][-1].append((o, t))
        else:
            raise ValueError(f"{path}: 无法解析：{ln}")
    for e in entries:
        e["paras"] = [p for p in e["paras"] if p]
    return heading, entries


def is_wiki_source(url):
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain)
               for domain in ("wikisource.org", "wikipedia.org"))


def page(title, body, r, extra_js=False):
    js = f'<script src="{r}assets/reader.js" defer></script>' if extra_js else ""
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{CSS_LINK.format(r=r)}
<script src="{r}assets/theme.js"></script>
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
            f'<span class="s" tabindex="0" data-t="{esc(t2)}">{orig_html(o2)}</span>'
            for o, t in para for o2, t2 in split_pairs(o, t)
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
    pslug, ptitle, pord, nvol = part[:4]
    is_xu = len(part) > 4
    heading, entries = parse_juan(src_path)
    r = "../../"
    toc = "".join(f'<li><a href="#e{i}">{esc(e["title"])}</a></li>' for i, e in enumerate(entries, 1))
    prev_html = (f'<a href="juan{vol-1:02d}.html">← 卷{cn(vol-1)}</a>' if (vol - 1) in avail
                 else '<span class="off">&nbsp;</span>')
    next_html = (f'<a href="juan{vol+1:02d}.html">卷{cn(vol+1)} →</a>' if (vol + 1) in avail
                 else '<span class="off">下一卷：待整理</span>')
    if is_xu:
        prev_html = next_html = '<span class="off">&nbsp;</span>'
    body = f"""<header class="top">
{crumbs([("古典文库", r + "index.html"), (book["title"], "../index.html"), (ptitle, None)])}
<h1>{esc(ptitle)}<small>{esc(pord)}</small></h1>
<h2>{esc(heading)}</h2>
</header>
<main class="reading-layout">
<details class="toc" open><summary>本卷目录</summary><ol>{toc}</ol></details>
<div class="reading-content">
{chr(10).join(render_entry(i, e) for i, e in enumerate(entries, 1))}
<nav class="pager">{prev_html}<a href="../index.html">目录</a>{next_html}</nav>
</div>
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
    for part in book["parts"]:
        pslug, ptitle, pord, nvol = part[:4]
        cells = []
        for v in range(1, nvol + 1):
            label = part[4] if len(part) > 4 else f"卷{cn(v)}"
            if (pslug, v) in done:
                count = "" if len(part) > 4 else f"<small>{done[(pslug, v)]}则</small>"
                cells.append(f'<li class="ok"><a href="{pslug}/juan{v:02d}.html">{label}{count}</a></li>')
            else:
                cells.append(f'<li class="todo"><span>{label}<small>待整理</small></span></li>')
        sections.append(f'<section class="part"><h2>{esc(ptitle)}<small>{esc(pord)}{'' if len(part) > 4 else f' · 共{nvol}卷'}</small></h2><ul class="vols">{"".join(cells)}</ul></section>')
    body = f"""<header class="top">
{crumbs([("古典文库", "../index.html"), (book["title"], None)])}
<h1>{esc(book["title"])}<small>{esc(book["author"])}</small></h1>
{intro_html(book["slug"])}
</header>
<main>{"".join(sections)}</main>
<footer>已整理 {sum(n for (p, _), n in done.items() if p != "xu")} 则。</footer>"""
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
SHIJING_PAGES = [
    ("xu", "毛诗序"),
    ("zhounan", "周南"), ("shaonan", "召南"), ("beifeng", "邶风"), ("yongfeng", "鄘风"),
    ("weifeng", "卫风"), ("wangfeng", "王风"), ("zhengfeng", "郑风"), ("qifeng", "齐风"),
    ("weifeng2", "魏风"), ("tangfeng", "唐风"), ("qinfeng", "秦风"), ("chenfeng", "陈风"),
    ("guifeng", "桧风"), ("caofeng", "曹风"), ("binfeng", "豳风"),
    ("xiaoya", "小雅"), ("daya", "大雅"), ("songzhou", "周颂"), ("lusong", "鲁颂"), ("shangsong", "商颂"),
]
GUWEN_PAGES = [
    ("xu", "序一、序二、例言"), ("juan01", "卷一·周文"), ("juan02", "卷二·周文"), ("juan03", "卷三·周文"), ("juan04", "卷四·战国文"),
    ("juan05", "卷五·秦汉文"), ("juan06", "卷六·汉文"), ("juan07", "卷七·六朝唐文"), ("juan08", "卷八·唐文"),
    ("juan09", "卷九·唐宋文"), ("juan10", "卷十·宋文"), ("juan11", "卷十一·宋文"), ("juan12", "卷十二·明文"),
]
SHISHUO_PAGES = [
    ("xu", "序"),
    ("dexing", "德行第一"), ("yanyu", "言语第二"), ("zhengshi", "政事第三"), ("wenxue", "文学第四"),
    ("fangzheng", "方正第五"), ("yaliang", "雅量第六"), ("shijian", "识鉴第七"), ("shangyu", "赏誉第八"),
    ("pinzao", "品藻第九"), ("guizhen", "规箴第十"), ("jiewu", "捷悟第十一"), ("suhui", "夙惠第十二"),
    ("haoshuang", "豪爽第十三"), ("rongzhi", "容止第十四"), ("zixin", "自新第十五"), ("qixian", "企羡第十六"),
    ("shangshi", "伤逝第十七"), ("qiyi", "栖逸第十八"), ("xianyuan", "贤媛第十九"), ("shujie", "术解第二十"),
    ("qiaoyi", "巧艺第二十一"), ("chongli", "宠礼第二十二"), ("rendan", "任诞第二十三"), ("jianao", "简傲第二十四"),
    ("paidiao", "排调第二十五"), ("qingdi", "轻诋第二十六"), ("jiajue", "假谲第二十七"), ("chumian", "黜免第二十八"),
    ("jinse", "俭啬第二十九"), ("taichi", "汰侈第三十"), ("fenjuan", "忿狷第三十一"), ("chanxian", "谗险第三十二"),
    ("youhui", "尤悔第三十三"), ("pilou", "纰漏第三十四"), ("huoni", "惑溺第三十五"), ("chouxi", "仇隙第三十六"),
]
def _shiji_pages():
    import json
    d = json.loads((ROOT / "shiji_pages.json").read_text(encoding="utf8"))
    out = []
    for grp, items in d:
        out.append((None, grp))
        out += [(f"juan{n:03d}", t) for n, t in items]
    return out


def _liaozhai_spec():
    import json
    progress = json.loads((ROOT / "sources/liaozhai/progress.json").read_text(encoding="utf8"))
    volumes = progress["volumes"]
    complete = sum(e["status"] == "complete" and e.get("kind") != "group"
                   for v in volumes for e in v.get("entries", []))
    drafts = sum(e["status"] == "draft" for v in volumes for e in v.get("entries", []))
    all_done = (all(v["status"] == "complete" for v in volumes)
                and progress["preface_status"] == "complete")
    status = (f"十二卷{complete}篇正文及《聊斋自志》全部整理完成；另保留卷十二附录分组说明。"
              if all_done else f"目前已整理{complete}篇，全文仍在整理中。")
    if drafts:
        status += f"另有{drafts}篇注译初稿待扩写复核，不计入完成篇数。"
    page_sources = {}
    if progress.get("preface_review", {}).get("source") == "wikisource":
        page_sources["zizhi"] = progress["preface_review"]
    for volume in volumes:
        entries = volume.get("entries", [])
        wiki_entries = [e for e in entries if e.get("review", {}).get("source") == "wikisource"]
        if wiki_entries:
            source = dict(wiki_entries[0]["review"])
            if len(wiki_entries) != len(entries):
                source["prefix"] = f"本卷第{int(wiki_entries[0]['id'])}—{int(wiki_entries[-1]['id'])}篇原文据"
                source["after"] = "此前各篇保留原扫描底本校录；"
            if any(e["status"] == "draft" for e in entries):
                source["after"] = source.get("after", "") + "本卷白话仍有速记式初稿，待逐句扩写复核，不代表整理完成；"
            page_sources[f"juan{volume['volume']:02d}"] = source
    return {"title": "聊斋志异", "author": "［清］蒲松龄", "unit": "篇",
            "count_entries": True, "summary_unit": "篇",
            "count": lambda secs: (sum(bool(s["chunks"]) for s in secs), "篇"),
            "index_footer": status,
            "page_sources": page_sources,
            "intro": "",
            "pages": [("zizhi", "聊斋自志")] + [
                (f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}" +
                 ("（整理中）" if v["status"] == "in_progress" else "")) for v in volumes
            ]}


def _huainanzi_spec():
    import json
    progress = json.loads((ROOT / "sources/huainanzi/progress.json").read_text(encoding="utf8"))
    complete = sum(e["status"] == "complete" for v in progress["volumes"] for e in v.get("entries", []))
    completed_volumes = [f"卷{cn(v['volume'])}" for v in progress["volumes"] if v["status"] == "complete"]
    status = ("二十一卷全部整理完成。" if len(completed_volumes) == 21 else
              ("已完成" + "、".join(completed_volumes) + "，其余正文待整理。" if completed_volumes else "全文仍在整理中。"))
    return {"title": "淮南子", "author": "［西汉］刘安及其门客", "unit": "节",
            "page_sources": {"xu": _xu_source("huainanzi"), **{f"juan{v['volume']:02d}": next(e["review"] for e in v["entries"] if e.get("review", {}).get("source") == "wikisource")
                             for v in progress["volumes"] if any(e.get("review", {}).get("source") == "wikisource" for e in v.get("entries", []))}},
            "intro": "",
            "pages": [("xu", "叙（高诱）")] + [(f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}·{v['title']}" +
                       ("（整理中）" if v["status"] == "in_progress" else "")) for v in progress["volumes"]]}


def _songlun_spec():
    import json
    progress = json.loads((ROOT / "sources/songlun/progress.json").read_text(encoding="utf8"))
    complete = sum(e["status"] == "complete" for v in progress["volumes"] for e in v.get("entries", []))
    completed = [f"卷{cn(v['volume'])}" for v in progress["volumes"] if v["status"] == "complete"]
    status = ("十五卷全部整理完成。" if len(completed) == 15 else
              ("已完成" + "、".join(completed) + "，其余正文待整理。" if completed else "全文仍在整理中。"))
    return {"title": "宋论", "author": "［清］王夫之", "unit": "篇",
            "count_entries": True, "summary_unit": "篇",
            "page_sources": {f"juan{v['volume']:02d}": next(e["review"] for e in v["entries"] if e.get("review", {}).get("source") == "wikisource")
                             for v in progress["volumes"] if any(e.get("review", {}).get("source") == "wikisource" for e in v.get("entries", []))},
            "intro": "",
            "pages": [(f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}·{v['title']}" +
                       ("（整理中）" if v["status"] == "in_progress" else "")) for v in progress["volumes"]]}


def _yantielun_spec():
    import json
    progress = json.loads((ROOT / "sources/yantielun/progress.json").read_text(encoding="utf8"))
    complete = sum(e["status"] == "complete" for v in progress["volumes"] for e in v["entries"])
    completed = [f"卷{cn(v['volume'])}" for v in progress["volumes"] if v["status"] == "complete"]
    status = ("十卷六十篇全部整理完成。" if complete == 60 else
              ("已完成" + "、".join(completed) + "，其余正文待整理。" if completed else "全文仍在整理中。"))
    return {"title": "盐铁论", "author": "［西汉］桓宽", "unit": "篇",
            "count_entries": True, "summary_unit": "篇",
            "page_sources": {f"juan{v['volume']:02d}": next(e["review"] for e in v["entries"] if e.get("review", {}).get("source") == "wikisource")
                             for v in progress["volumes"] if any(e.get("review", {}).get("source") == "wikisource" for e in v["entries"])},
            "intro": "",
            "pages": [(f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}" +
                       ("（整理中）" if v["status"] == "in_progress" else "")) for v in progress["volumes"]]}


def _yuewei_spec():
    import json
    progress = json.loads((ROOT / "sources/yuewei/progress.json").read_text(encoding="utf8"))
    stories = sum(e.get("kind") == "story" and e["status"] == "complete"
                  for v in progress["volumes"] for e in v.get("entries", []))
    completed = [f"卷{cn(v['volume'])}" for v in progress["volumes"] if v["status"] == "complete"]
    status = ("二十四卷全部整理完成。" if len(completed) == 24 else
              ("已完成" + "、".join(completed) + "，其余正文待整理。" if completed else "全文仍在整理中。"))
    return {"title": "阅微草堂笔记", "author": "［清］纪昀", "unit": "项",
            "count_entries": True, "summary_unit": "项",
            "page_sources": {f"juan{v['volume']:02d}": next(e["review"] for e in v["entries"] if e.get("review", {}).get("source") == "wikisource")
                             for v in progress["volumes"] if any(e.get("review", {}).get("source") == "wikisource" for e in v.get("entries", []))},
            "intro": "",
            "pages": [(f["slug"], f["title"]) for f in progress["front_matter"]] + [
                (f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}·{v['title']}" +
                 ("（整理中）" if v["status"] == "in_progress" else "")) for v in progress["volumes"]]}


def _mudanting_spec():
    pages = []
    for d in sorted((ROOT / "src/mudanting").glob("[0-9][0-9]")):
        head = (d / "01.txt").read_text(encoding="utf8").splitlines()[0][2:].strip()
        no, _, name = head.partition(" ")
        pages.append((d.name, f"{no}·{name}"))
    if (ROOT / "src/mudanting/fu/01.txt").exists():
        pages.append(("fu", "附·杜丽娘慕色还魂话本"))
    return {"title": "牡丹亭", "author": "［明］汤显祖", "unit": "出", "no_tip": True, "side_toc": True,
            "intro": "",
            "pages": pages}


def _jinpingmei_spec():
    catalog = json.loads((ROOT / "sources/jinpingmei/chapters.json").read_text(encoding="utf8"))
    pages = []
    for entry in catalog:
        slug = entry["slug"]
        if slug != "xu" and (int(slug) - 1) % 10 == 0:
            n = int(slug)
            pages.append((None, f"第{cn(n)}回至第{cn(n + 9)}回"))
        pages.append((slug, entry["title"]))
    return {
        "title": "金瓶梅（崇祯本）", "author": "［明］兰陵笑笑生", "unit": "回",
        "prose": True, "no_tip": True, "side_toc": True, "home_intro_own": True,
        "reading_hint": "", "no_count": True, "pages": pages,
        "index_footer": "崇祯本，收序及一百回。",
        "page_options": {e["slug"]: {"footer": "崇祯本正文。"} for e in catalog},
        "page_sources": {e["slug"]: {"url": e["url"], "revision": e["revision"]} for e in catalog},
    }


def _plain_novel_spec(slug, title, author, unit, count):
    catalog = json.loads((ROOT / "sources" / slug / "chapters.json").read_text(encoding="utf8"))
    pages = []
    for entry in catalog:
        key = entry["slug"]
        if key.isdigit() and (int(key) - 1) % 10 == 0:
            n = int(key)
            pages.append((None, f"第{cn(n)}{unit}至第{cn(min(n + 9, count))}{unit}"))
        pages.append((key, entry["title"]))
    return {
        "title": title, "author": author, "unit": unit, "pages": pages,
        "prose": True, "no_tip": True, "side_toc": True, "home_intro_own": True,
        "reading_hint": "", "no_count": True, "omit_source_credit": True,
        "index_footer": f"全书{cn(count)}{unit}。" if slug != "erke" else "收序及四十卷。",
        "page_options": {e["slug"]: {"footer": ""} for e in catalog},
    }


def _rulinwaishi_spec():
    catalog = json.loads((ROOT / "sources/rulinwaishi/chapters.json").read_text(encoding="utf8"))
    pages = []
    for entry in catalog:
        slug = entry["slug"]
        if (int(slug) - 1) % 10 == 0:
            n = int(slug)
            pages.append((None, f"第{cn(n)}回至第{cn(min(n + 9, len(catalog)))}回"))
        pages.append((slug, entry["title"]))
    return {
        "title": "儒林外史", "author": "［清］吴敬梓", "unit": "回",
        "prose": True, "no_tip": True, "side_toc": True, "home_intro_own": True,
        "reading_hint": "", "no_count": True, "pages": pages,
        "index_footer": "全书五十六回。", "omit_source_credit": True,
        "page_options": {e["slug"]: {"footer": ""} for e in catalog},
        "page_sources": {e["slug"]: {"url": e["url"], "revision": e["revision"]} for e in catalog},
    }


def _sanyan_spec(slug, title):
    entries = json.loads((ROOT / "sources" / slug / "chapters.json").read_text(encoding="utf8"))
    pages = [(p["slug"], p["title"]) for p in entries]
    return {"title": title, "author": "［明］冯梦龙辑", "unit": "卷",
            "prose": True, "no_tip": True, "side_toc": True, "no_count": True,
            "wide_index": True, "home_intro_own": True, "pages": pages,
            "reading_hint": "", "index_footer": "",
            "page_options": {key: {"footer": ""} for key, _ in pages}}


def _laocanyoujixuji_spec():
    base = ROOT / "sources/laocanyoujixuji"
    catalog = json.loads((base / "catalog.json").read_text(encoding="utf8"))
    pages = [(p["slug"], p["title"]) for p in catalog]
    return {"title": "老残游记续集", "author": "［清］刘鹗", "unit": "回",
            "prose": True, "no_tip": True, "side_toc": True, "no_count": True,
            "wide_index": True, "home_intro_own": True, "pages": pages,
            "reading_hint": "", "index_footer": "",
            "page_options": {slug: {"footer": ""} for slug, _ in pages}}


def _laocanyouji_spec():
    base = ROOT / "sources/laocanyouji"
    catalog = json.loads((base / "catalog.json").read_text(encoding="utf8"))
    pages = [(p["slug"], p["title"]) for p in catalog]
    return {"title": "老残游记", "author": "［清］刘鹗", "unit": "回",
            "prose": True, "no_tip": True, "side_toc": True, "no_count": True,
            "wide_index": True, "home_intro_own": True,
            "pages": pages, "reading_hint": "", "index_footer": "",
            "page_options": {slug: {"footer": ""} for slug, _ in pages}}


def _hongloumeng_spec():
    pages = []
    for d in sorted((ROOT / "src/hongloumeng").glob("[0-9][0-9][0-9]")):
        n = int(d.name)
        if (n - 1) % 10 == 0:
            pages.append((None, f"第{cn(n)}回至第{cn(n + 9)}回"))
        head = (d / "01.txt").read_text(encoding="utf8").splitlines()[0][2:].strip()
        no, _, name = head.partition(" ")
        pages.append((d.name, f"{no}·{name}"))
    return {"title": "红楼梦", "author": "［清］曹雪芹、高鹗", "unit": "回", "prose": True, "no_tip": True, "side_toc": True, "center_poems": True, "reading_hint": "",
            "intro": "",
            "pages": pages}


def _xianqing_spec():
    import json
    progress = json.loads((ROOT / "sources/xianqing/progress.json").read_text(encoding="utf8"))
    return {"title": "闲情偶寄", "author": "［清］李渔", "unit": "项",
            "count_entries": True, "summary_unit": "项",
            "intro": "",
            "pages": [(f["slug"], f["title"]) for f in progress["front_matter"]] + [
                (f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}·{v['title']}") for v in progress["volumes"]]}


def _xiaochuang_spec():
    import json
    progress = json.loads((ROOT / "sources/xiaochuang/progress.json").read_text(encoding="utf8"))
    translated = sum(p.get("translated_paragraphs", 0) for p in progress["pages"])
    notes = sum(p.get("editor_notes", 0) for p in progress["pages"])
    return {"title": "小窗幽记", "author": "［明］陆绍珩 选，陆绍琏 阅", "unit": "项",
            "count": lambda secs: (sum(1 for s in secs if s["title"].isdigit()), "则"),
            "no_tip": True, "side_toc": True, "count_entries": True, "summary_unit": "项",
            "original_only": True,
            "intro": "",
            "index_footer": f"原文收录1547段；已配白话与编者注释{translated}段。原站校勘记另列，不计作编者注释。",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_options": {p["slug"]: {"no_tip": False,
                  "reading_hint": "本卷已配逐句白话与独立注释。卷末另附原站校勘记。",
                  "footer": "白话、题解与独立注释为编者自撰；疑字保留并注出暂解。卷末校勘记为原站文字，未据影印本逐字校勘。"}
                             for p in progress["pages"] if p["status"] == "annotated"},
            "page_sources": {p["slug"]: p["source"] for p in progress["pages"]}}


def _canying_spec():
    import json
    progress = json.loads((ROOT / "sources/canying/progress.json").read_text(encoding="utf8"))
    completed = progress.get("annotated_paragraphs", [])
    status = ((f"已完成全部{len(completed)}段的逐句白话、题解与分条注释。" if len(completed) == 390
               else f"已完成第1—{len(completed)}段的逐句白话、题解与分条注释，其余段落保留原文阅读版。")
              if completed else "白话与编者释义待整理。")
    return {"title": "餐樱庑随笔", "author": "［清］况周颐", "unit": "段",
            "prose": True, "no_tip": True, "original_only": True,
            "count_entries": True, "summary_unit": "段",
            "reading_hint": "原文阅读版；白话译文与编者释义尚待整理。括号内为底本夹注，〔缺字〕标记原站未能显示的旧字库字形。左侧编号沿用原站段号。",
            "original_footer": "底本夹注保留在正文括号中；未据影印本逐字校勘。分页与目录摘句为整理者所加，不代表原书卷目。",
            "intro": "",
            "index_footer": f"原文收录390段；已配白话、题解与编者注释{len(completed)}段。",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_options": {p["slug"]: {"no_tip": False,
                  "reading_hint": "括号内仍保留底本夹注，疑字、缺字的辨读见注释。",
                  "footer": "白话、题解与词条注释为编者自撰；原站夹注保留在正文括号中。疑字另注，原文尚未据影印本逐字校定。"}
                             for p in progress["pages"] if p.get("annotation_status") == "complete"},
            "page_sources": {p["slug"]: p["source"] for p in progress["pages"]}}


def _four_classics_spec(slug):
    import json
    import sys
    # Editorial metadata is shared with the reproducible source preparation tool.
    sys.path.insert(0, str(ROOT / "tools"))
    from four_classics_notes import META
    meta = META[slug]
    progress = json.loads((ROOT / "sources" / slug / "progress.json").read_text(encoding="utf8"))
    return {"title": meta["title"], "author": meta["author"], "unit": meta["unit"],
            "prose": meta["prose"], "no_tip": True, "side_toc": True,
            "center_poems": slug in ("xiyouji", "shuihuzhuan", "sanguoyanyi", "roupotuan"),
            "count_entries": False,
            **({"count": lambda secs: (sum(1 for s in secs if s["title"].endswith("折")), "折")}
               if slug == "xixiangji" else {"no_count": True}),
            "index_footer": f"正文 {progress['chapter_count']} {meta['unit']}；另收全书题解及所选版本附文。",
            "reading_hint": "" if slug in ("xiyouji", "shuihuzhuan", "sanguoyanyi", "roupotuan") else "原文直读。附基础导读注释，不设白话译文。",
            "intro": "",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"] if p["slug"] != "tijie"],
            "page_sources": {p["slug"]: p["source"] for p in progress["pages"] if "source" in p}}


def _shangjunshu_spec():
    import json
    progress = json.loads((ROOT / "sources/shangjunshu/progress.json").read_text(encoding="utf8"))
    return {"title": "商君书", "author": "［战国］商鞅及后学（旧题商鞅）", "unit": "目",
            "count_entries": True, "summary_unit": "目",
            "intro": "",
            "index_footer": "五卷26目：24篇现存正文，另2目正文亡佚。",
            "pages": [(f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}") for v in progress["volumes"]],
            "page_sources": {f"juan{v['volume']:02d}": v["source"] for v in progress["volumes"]}}


def _zuozhuan_spec():
    import json
    progress = json.loads((ROOT / "sources/zuozhuan/progress.json").read_text(encoding="utf8"))
    return {"title": "春秋左传", "author": "［春秋］左丘明（相传）", "unit": "年",
            "count_entries": False,
            "count": lambda secs: (len({s["title"].split("·")[0] for s in secs}), "年"),
            "intro": "",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_sources": {p["slug"]: p["source"] for p in progress["pages"]}}


def _zhenglun_changyan_spec():
    import json
    progress = json.loads((ROOT / "sources/zhenglun-changyan/progress.json").read_text(encoding="utf8"))
    pages = progress["pages"]
    body = next(p for p in pages if p["slug"] == "zhenglun")
    done = sum(u["status"] == "complete" for u in body["units"])
    changyan = [u for p in pages if p["slug"].startswith("changyan") for u in p["units"]]
    changyan_done = sum(u["status"] == "complete" for u in changyan)
    status = (f"《政论》正文{done}/{len(body['units'])}段、《昌言》含资料附录{changyan_done}/{len(changyan)}段已注译。"
              + ("所据辑本整理完成。" if progress["status"] == "complete" else "合目尚未完成。"))
    return {"title": "政论·昌言", "author": "［东汉］崔寔／仲长统", "unit": "项",
            "count_entries": True, "summary_unit": "项", "index_footer": status,
            "intro": "",
            "pages": [(p["slug"], p["title"]) for p in pages],
            "page_sources": {p["slug"]: dict(p["source"], after="底本〈夹注〉原样分条移入注释，原位映射保存在来源进度中；")
                             for p in pages if "source" in p},
            "page_options": {p["slug"]: {"footer": "白话、题解及释词为编者自撰；标作底本夹注的异文、引书说明沿用维基辑本，分别保留，不混署古作者。"}
                             for p in pages}}


def _mengxi_spec():
    import json
    progress = json.loads((ROOT / "sources/mengxi/progress.json").read_text(encoding="utf8"))
    pages = progress["pages"]
    total = sum(len(p["units"]) for p in pages)
    done = sum(u["status"] == "complete" for p in pages for u in p["units"])
    status = f"已注译{done}/{total}个原文段落单元；段落不等同原书条数。全书整理中。"
    return {"title": "梦溪笔谈", "author": "［北宋］沈括", "unit": "段",
            "count_entries": True, "summary_unit": "段", "index_footer": status,
            "intro": "",
            "pages": [(p["slug"], p["title"] + (f"（已译{sum(u['status'] == 'complete' for u in p['units'])}/{len(p['units'])}段）"
                       if p.get("annotation_status") == "in_progress" else "")) for p in pages],
            "page_sources": {p["slug"]: p["source"] for p in pages if "source" in p}}


def _zhanguoce_spec():
    progress = json.loads((ROOT / "sources/zhanguoce/progress.json").read_text(encoding="utf8"))
    body_pages = [p for p in progress["pages"] if p["slug"] not in [f"{prefix}{i:02}" for prefix in ("xu", "fu") for i in range(1, 7)]]
    done = sum(u["status"] == "complete" and u.get("kind") != "source_note_appendix" for p in body_pages for u in p["units"])
    finished = len(body_pages) == 33 and all(u["status"] == "complete" for p in progress["pages"] for u in p["units"])
    status = (f"所据士礼居本三十三卷{done}篇策文、六篇序、六篇附文及底本附引1项均已注译。" if finished else f"已注译{done}篇策文，全书整理中。") + "六篇序与六篇附文各合为一个阅读条目，每篇只列一个目录标题。"
    return {"title": "战国策（士礼居丛书本）", "author": "［汉］刘向编｜［清］黄丕烈札记",
            "unit": "项", "summary_unit": "项", "count_entries": True, "strict_pairs": True, "side_toc": True,
            "index_footer": status,
            "intro": "",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_sources": {p["slug"]: dict(p["source"], after="底本夹注分条移入注释；卷首注附于首篇，原位映射另存。题解、白话与编者释词为自撰。") for p in progress["pages"]},
            "page_options": {p["slug"]: {"footer": "本页原作／材料署名：" + p.get("author", "刘向编，士礼居本所录诸家校注") + "。原注与编者自撰题解、白话、释词分别标明；疑文照录，未补造佚文。"} for p in progress["pages"]}}


def _zhanguoce_grouped_spec():
    spec = _zhanguoce_spec()
    config = json.loads((ROOT / "sources/zhanguoce/reading-groups.json").read_text(encoding="utf8"))
    groups = config["groups"]
    members = {old: g for g in groups for old in g["members"]}
    pages = []
    for slug, title in spec["pages"]:
        if slug not in members:
            pages.append((slug, title))
        elif slug == members[slug]["members"][0]:
            pages.append((members[slug]["slug"], members[slug]["title"]))
    spec["pages"] = pages
    spec["page_redirects"] = {old: f'{g["slug"]}.html#e{i}' for g in groups for i, old in enumerate(g["members"], 1)}
    spec["section_sources"] = {g["slug"]: {e["title"]: dict(e["source"], author=e["author"]) for e in g["entries"]} for g in groups}
    for g in groups:
        spec["page_sources"][g["slug"]] = dict(url="https://zh.wikisource.org/wiki/戰國策_(士禮居叢書本)", label="维基文库士礼居本目录", after="每篇的原署、来源和修订号分别列于篇首；完整段落合属一篇，不列分段目录。")
        spec["page_options"][g["slug"]] = {"footer": "每篇保留原文段落、逐句白话、独立分行原注及编者注；原始分段稿和原位映射另存供核验。"}
    return spec


def _annotated_selection(slug, title, footer):
    progress = json.loads((ROOT / "sources" / slug / "progress.json").read_text(encoding="utf8"))
    pages = [p for p in progress["pages"] if p["status"] == "complete"]
    catalog = progress.get("catalog")
    order = (json.loads((ROOT / "sources" / slug / catalog).read_text(encoding="utf8"))["pages"]
             if catalog else pages)
    display = [(p["slug"], p["title"]) for p in order]
    if slug == "shangshu":
        witness = json.loads((ROOT / "sources/shangshu/catalog.json").read_text(encoding="utf8"))
        titles = {p["slug"]: p["title"] for p in pages}
        display = [(None, "卷首"), ("shuxu", "书序")]
        group = None
        for p in witness:
            if p["group"] != group:
                group = p["group"]
                display.append((None, group))
            display.append((p["slug"], titles.get(p["slug"], p["title"].split("，原文见", 1)[0])))
        completed = sum(p["slug"] != "shuxu" for p in pages)
        preface = "书序另列，已注译" if "shuxu" in titles else "书序另列"
        footer = f"传世正文{len(witness)}篇，已完成{completed}篇逐句注译；{preface}。清华简不计入传世篇数。"
    if catalog:
        footer = f"全书{len(order)}篇，已完成{len(pages)}篇逐句注译。"
    return {"title": title, "author": "［西汉］戴圣辑" if slug == "liji" else "［先秦］佚名", "unit": "节", "intro": "",
            "count_entries": True, "strict_pairs": True, "side_toc": True,
            "index_footer": footer, "visible_intro_credit": slug == "shangshu",
            "pages": display,
            "page_sources": {p["slug"]: dict(p["source"], label="维基文库",
                            after="原文据所列修订；分节标题、题解、白话与释词为本库整理。") for p in pages}}


def _xunzi_spec():
    spec = _annotated_selection("xunzi", "荀子", "")
    root = ROOT / "sources/xunzi"
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf8"))
    pages, volume = [], None
    for entry in catalog["pages"]:
        if entry["volume"] != volume:
            volume = entry["volume"]
            pages.append((None, f"第{cn(volume)}卷" if volume else "卷首"))
        pages.append((entry["slug"], entry["title"]))
    done = spec["page_sources"]
    count = sum(slug != "xu" for slug in done)
    spec.update(author="［战国］荀况", unit="节", pages=pages, visible_intro_credit=True,
                index_footer=f"全书二十卷三十二篇，已完成{count}篇逐句注译；《荀子序》另列。")
    return spec


def _jiayou_spec():
    spec = _annotated_selection("jiayou", "嘉祐集", "")
    progress = json.loads((ROOT / "sources/jiayou/progress.json").read_text(encoding="utf8"))
    finished = sum(p["status"] == "complete" for p in progress["pages"])
    spec.update(author="［北宋］苏洵", unit="篇",
                index_footer=f"卷一至卷十六及补遗，共17项；已完成{finished}项逐句注译。")
    return spec


def _classics_spec():
    entries = json.loads((ROOT / "sources" / "classic_list" / "entries.json").read_text(encoding="utf8"))
    return {"title": "经典名篇", "author": "个人选藏", "unit": "篇",
            "count_entries": True, "strict_pairs": True, "side_toc": True, "wide_index": True,
            "intro": "",
            "pages": [(e["slug"], e["title"] + "｜" + e["author"]) for e in entries],
            "section_sources": {e["slug"]: {sec["title"]: dict(sec["source"], author=sec.get("author", e["author"]))
                                           for sec in e["sections"]} for e in entries if "sections" in e},
            "page_redirects": {old: target for e in entries for old, target in e.get("redirects", {}).items()},
            "page_sources": {e["slug"]: e["source"] for e in entries if "source" in e},
            "index_footer": f"已整理{len(entries)}项（《过秦论》上中下合列一项，《永州八记》八篇合列一项，三苏《六国论》合列一项）。底本疑误保留加注；赵秉忠策文所据电子本尚待影像校勘。"}


def _zengguofan_spec():
    progress = json.loads((ROOT / "sources/zengguofan/progress.json").read_text(encoding="utf8"))
    done, total = progress["annotated_letters"], progress["letters"]
    return {"title": "曾国藩家书", "author": "［清］曾国藩", "unit": "篇",
            "prose": True, "count_entries": True, "strict_pairs": True,
            "intro": "",
            "index_footer": f"三章{done}/{total}封家信及9项附文全部完成注译，共{progress['annotated_sentences']}句白话、{progress['notes']}条注。维基文库目录所列第四章无正文。",
            "reading_hint": "",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_sources": {p["slug"]: {**p["source"], "after": "整理夹注内句末标点，并删除段末孤立的残引号、间隔点；疑字照录，原站标题与日期不合处另注。"}
                             for p in progress["pages"]}}


def _zizhitongjian_spec():
    cat = json.loads((ROOT / "sources/zizhitongjian/catalog.json").read_text(encoding="utf8"))

    def year(y):
        return f"前{-y}" if y < 0 else str(y)
    pages = []
    for ji in cat["ji"]:
        pages.append((None, f"{ji['name']}（卷{cn(ji['first'])}至卷{cn(ji['last'])}，共{ji['volumes']}卷）"))
        for v in cat["volumes"]:
            if v["ji"] == ji["name"]:
                span = year(v["start_year"]) if v["start_year"] == v["end_year"] else f"{year(v['start_year'])}—{year(v['end_year'])}"
                pages.append((v["slug"], f"卷{cn(v['n'])}·{v['name']}｜{span}"))
    fulu = json.loads((ROOT / "sources/zizhitongjian/progress.json").read_text(encoding="utf8"))["pages"]
    pages.append((None, f"附录（{len(fulu)}篇）"))
    pages.extend((p["slug"], p["title"]) for p in fulu)
    jp = ROOT / "sources/zizhitongjian/progress_juan.json"
    juan = json.loads(jp.read_text(encoding="utf8"))["pages"] if jp.exists() else []
    return {"title": "资治通鉴", "author": "［宋］司马光 撰，［元］胡三省 音注", "unit": "卷", "summary_unit": "卷", "wide_index": True, "no_count": True,
            "intro": "",
            "index_footer": "周纪至五代各纪（卷一至卷二百九十四）已整理：按年分节，配逐句白话、题解与注释，点校者的校刊记另列于卷末。"
                            "附录含新注序、宋神宗序、进书表、奖谕诏书、校勘人姓名、释例，以及刘恕《资治通鉴外纪》序和卷四至卷十（外纪卷一至卷三在维基文库仅见四库全书本，未收）。"
                            "纪年起止据各卷卷首“起…尽…凡…年”换算，个别卷首缺载者据正文年份标目推得，详见 sources/zizhitongjian/README.md。",
            "page_sources": {p["slug"]: {**p["source"], "after": "原站点校者以〔　〕补入、以（　）删去的字，已按校改后的定本录入，段首校记序号去掉；"} for p in juan},
            "pages": pages}


def _prose_pages_spec(slug, title, author, footer, groups):
    """《东京梦华录》《传习录》：页表读自 sources/<slug>/progress.json；groups 把页按卷分组。"""
    progress = json.loads((ROOT / f"sources/{slug}/progress.json").read_text(encoding="utf8"))
    pages = []
    for name, prefixes in groups:
        members = [p for p in progress["pages"] if p["slug"].startswith(prefixes)]
        if members:
            pages.append((None, name))
            pages.extend((p["slug"], p["title"]) for p in members)
    return {"title": title, "author": author, "unit": "节", "summary_unit": "节", "wide_index": True,
            "index_footer": footer, "reading_hint": "",
            "pages": pages,
            "page_sources": {p["slug"]: {**p["source"], "after": "原站标点保持不变；"} for p in progress["pages"]}}


def _donglinghualu_spec():
    return _prose_pages_spec(
        "donglinghualu", "东京梦华录", "［宋］孟元老",
        "序及卷一至卷十全部整理完成；原站标点与文字保持不变，疑误字只在注中说明。", [("序", ("xu",)), ("正文", ("juan",))])


def _chuanxilu_spec():
    return _prose_pages_spec(
        "chuanxilu", "传习录", "［明］王守仁 撰，门人徐爱等 录",
        "卷上、中、下及序跋全部整理完成；条目编号为维基文库本所标，原站标点与文字保持不变，疑误字只在注中说明。",
        [("卷上", ("shang",)), ("卷中", ("zhong",)), ("卷下", ("xia",))])


def _xu_source(slug):
    """维基文库序页的出处信息，供序页页脚使用。"""
    d = json.loads((ROOT / f"sources/{slug}/wikisource/xu.json").read_text(encoding="utf8"))
    return {"title": d["title"], "url": d["url"], "revision": d["revision"], "after": "原站标点保持不变；疑误字只在注中说明。"}


def _works_spec(slug, title, author, unit, tijie=True, gloss=False, count=None, footer=None, groups=None):
    """关汉卿杂剧、赵氏孤儿等：页表读自 sources/<slug>/progress.json（页下按折/回分节）。"""
    progress = json.loads((ROOT / f"sources/{slug}/progress.json").read_text(encoding="utf8"))
    pages = [(p["slug"], p["title"]) for p in progress["pages"]]
    if groups:    # [(组名, 页数)]：在目录页按组加标题行
        grouped, i = [], 0
        for name, n in groups:
            grouped.append((None, name))
            grouped.extend(pages[i:i + n])
            i += n
        assert i == len(pages), (slug, i, len(pages))
        pages = grouped
    spec = {"title": title, "author": author, "unit": unit, "summary_unit": unit, "wide_index": True,
            "prose": not gloss, "no_tip": not gloss, "side_toc": True, "count_entries": False, "no_count": True,
            "intro": "", "pages": pages,
            "page_sources": {p["slug"]: p["source"] for p in progress["pages"]}}
    if not gloss:
        spec["reading_hint"] = "原文直读。附基础导读注释，不设白话译文。"
    if footer:
        spec["index_footer"] = footer
    return spec


def _dengxizi_spec():
    base = ROOT / "sources/dengxizi"
    pages = [("p01", "无厚"), ("p02", "转辞")]
    sources = {}
    for slug, _ in pages:
        witness = json.loads((base / f"{slug}.json").read_text(encoding="utf8"))
        sources[slug] = {k: witness[k] for k in ("url", "revision")}
    return {"title": "邓析子", "author": "［春秋］邓析（旧题）", "prose": True,
            "strict_pairs": True, "side_toc": True, "no_count": True, "pages": pages,
            "home_intro_own": True, "visible_intro_credit": True,
            "page_sources": sources, "reading_hint": "", "index_footer": "",
            "page_options": {slug: {"footer": ""} for slug, _ in pages}}


def _xuanzhenzi_spec():
    witness = json.loads((ROOT / "sources/xuanzhenzi/wikisource.json").read_text(encoding="utf8"))
    pages = [("p01", "卷上·碧虚"), ("p02", "卷中·惊驽"), ("p03", "卷下·涛之灵")]
    return {"title": "玄真子", "author": "［唐］张志和", "prose": True,
            "strict_pairs": True, "side_toc": True, "no_count": True, "pages": pages,
            "page_sources": {slug: {k: witness[k] for k in ("url", "revision")} for slug, _ in pages},
            "reading_hint": "", "index_footer": "",
            "page_options": {slug: {"footer": ""} for slug, _ in pages}}


def _dadailiji_spec():
    base = ROOT / "sources/dadailiji"
    catalog = json.loads((base / "index.json").read_text(encoding="utf8"))
    pages = [(p["slug"], p["title"]) for p in catalog["pages"]]
    sources = {}
    for slug, _ in pages:
        witness = json.loads((base / f"{slug}.json").read_text(encoding="utf8"))
        sources[slug] = {k: witness[k] for k in ("url", "revision")}
    return {"title": "大戴礼记", "author": "［西汉］戴德辑", "prose": True,
            "strict_pairs": True, "side_toc": True, "home_intro_own": True,
            "visible_intro_credit": True, "no_count": True, "pages": pages,
            "page_sources": sources, "reading_hint": "", "index_footer": "",
            "page_options": {slug: {"footer": ""} for slug, _ in pages}}


def _luoyangjialanji_spec():
    base = ROOT / "sources/luoyangjialanji"
    catalog = json.loads((base / "chapters.json").read_text(encoding="utf8"))
    return {
        "title": "洛阳伽蓝记", "author": "［北魏］杨衒之", "prose": True,
        "strict_pairs": True, "home_intro_own": True, "side_toc": True,
        "side_toc_always": True, "no_count": True, "wide_index": True,
        "omit_source_credit": True, "reading_hint": "",
        "pages": [(page["slug"], page["title"]) for page in catalog],
        "index_footer": "",
    }


def _fangyan_spec():
    catalog = json.loads((ROOT / "sources/fangyan/chapters.json").read_text(encoding="utf8"))
    return {
        "title": "方言", "author": "［西汉］扬雄", "prose": True,
        "strict_pairs": True, "home_intro_own": True, "side_toc": True,
        "side_toc_always": True, "no_count": True, "wide_index": True,
        "omit_source_credit": True, "reading_hint": "",
        "pages": [(page["slug"], page["title"]) for page in catalog],
        "index_footer": "",
    }


def _wenxuan_spec():
    def page_title(ch):
        if ch["slug"] == "xu":
            return "序"
        seen = []
        for sec in ch["sections"]:
            label = sec["path"][:2][-1] if sec["path"] else sec["title"]
            if label not in seen:
                seen.append(label)
        return f'{ch["title"]}·{"、".join(seen[:2])}' + ("等" if len(seen) > 2 else "")

    catalog = json.loads((ROOT / "sources/wenxuan/chapters.json").read_text(encoding="utf8"))
    return {
        "title": "昭明文选", "author": "［南朝梁］萧统编", "prose": True,
        "strict_pairs": True, "home_intro_own": True, "side_toc": True,
        "side_toc_always": True, "no_count": True, "wide_index": True,
        "omit_source_credit": True, "reading_hint": "",
        "pages": [(ch["slug"], page_title(ch)) for ch in catalog],
        "index_footer": "",
    }


def _lvshichunqiu_spec():
    base = ROOT / "sources/lvshichunqiu"
    catalog = json.loads((base / "chapters.json").read_text(encoding="utf8"))
    pages = [(p["slug"], p["title"]) for p in catalog]
    return {
        "title": "吕氏春秋", "author": "［战国］吕不韦门客编撰", "prose": True,
        "strict_pairs": True, "home_intro_own": True, "side_toc": True,
        "side_toc_always": True, "no_count": True, "wide_index": True,
        "omit_source_credit": True, "reading_hint": "",
        "pages": [(None, "十二纪"), *pages[:12], (None, "八览"), *pages[12:20], (None, "六论"), *pages[20:]],
        "index_footer": "",
    }


def _yili_spec():
    catalog = json.loads((ROOT / "sources/yili/chapters.json").read_text(encoding="utf8"))
    progress_path = ROOT / "sources/yili/progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf8")) if progress_path.exists() else []
    complete = len(progress) == len(catalog) and all(p["annotated"] == p["paragraphs"] for p in progress)
    return {
        "title": "仪礼", "author": "［先秦］佚名", "prose": True,
        "strict_pairs": True, "home_intro_own": True, "side_toc": True,
        "side_toc_always": True, "no_count": True, "wide_index": True, "unit": "篇",
        "pages": [(p["slug"], p["title"]) for p in catalog],
        "page_sources": {p["slug"]: {"url": p["url"], "revision": p["revision"]} for p in catalog},
        "index_footer": "十七篇全部注译完成。" if complete else "底本十七篇；白话与注释陆续整理。",
    }


def _xinlun_spec():
    catalog = json.loads((ROOT / "sources/xinlun/catalog.json").read_text(encoding="utf8"))
    pages = [("xu", "自序"), *((p["slug"], p["title"]) for p in catalog), ("appendix", "附录")]
    return {"title": "新论", "author": "［东汉］桓谭", "prose": True,
            "strict_pairs": True, "side_toc": True, "home_intro_own": True,
            "no_count": True, "wide_index": True, "pages": pages,
            "page_sources": {p["slug"]: {k: p[k] for k in ("url", "revision")} for p in catalog},
            "reading_hint": "", "index_footer": "", "omit_source_credit": True,
            "page_options": {slug: {"footer": ""} for slug, _ in pages}}


def _guoyu_spec():
    catalog = json.loads((ROOT / "sources/guoyu/catalog.json").read_text(encoding="utf8"))
    pages = [(p["slug"], p["title"]) for p in catalog]
    return {"title": "国语", "author": "［先秦］旧题左丘明", "prose": True,
            "strict_pairs": True, "side_toc": True, "home_intro_own": True,
            "no_count": True, "wide_index": True, "pages": pages,
            "page_sources": {p["slug"]: {k: p[k] for k in ("url", "revision")} for p in catalog},
            "reading_hint": "", "index_footer": "",
            "page_options": {slug: {"footer": ""} for slug, _ in pages}}


def _zhouli_spec():
    catalog = json.loads((ROOT / "sources/zhouli/catalog.json").read_text(encoding="utf8"))
    return {
        "title": "周礼", "author": "［古籍］撰人未详", "prose": True,
        "strict_pairs": True, "home_intro_own": True, "visible_intro_credit": True,
        "no_count": True, "wide_index": True, "unit": "篇",
        "pages": [(p["slug"], p["title"]) for p in catalog],
        "page_sources": {p["slug"]: {"url": p["url"], "revision": p["revision"]} for p in catalog},
        "reading_hint": "", "index_footer": "",
        "page_options": {p["slug"]: {"footer": "底本字形与阙文标记照录。"} for p in catalog},
    }


def _mozi_spec():
    witness = json.loads((ROOT / "sources/mozi/wikisource.json").read_text(encoding="utf8"))
    pages, page_options, page_sources = [], {}, {}
    missing = set()
    volume = 0
    annotated = available = 0
    for p in witness["pages"]:
        slug = p["slug"]
        if p["volume"] != volume:
            volume = p["volume"]
            pages.append((None, "卷" + cn(volume)))
        pages.append((slug, p["title"]))
        if p["missing"]:
            missing.add(slug)
            continue
        files = sorted((SRC / "mozi" / slug).glob("*.txt"))
        originals = [line for f in files for line in f.read_text(encoding="utf8").splitlines()
                     if line.startswith("原：")]
        available += bool(originals)
        translated = bool(originals) and all("||" in line for line in originals)
        annotated += translated
        page_options[slug] = {"no_tip": not translated}
        if not translated:
            page_options[slug].update(
                reading_hint="本篇可读原文，逐句白话与注释待整理。",
                footer="保留电子底本字形及缺字标记；尚未据影印本逐字校勘。")
        page_sources[slug] = {"url": witness["url"] + "#" + p["anchor"],
                              "revision": witness["revision"]}
    return {"title": "墨子", "author": "［先秦］墨翟及墨家后学",
            "unit": "篇", "prose": True, "strict_pairs": True, "side_toc": True,
            "home_intro_own": True, "visible_intro_credit": True, "missing_slugs": missing,
            "pages": pages, "page_options": page_options, "page_sources": page_sources,
            "index_footer": f"现存53篇，已收原文 {available}/53 篇，已完成逐句注译 {annotated}/53 篇；维基文库目录所标阙篇单列。"}


def _hanfeizi_spec():
    catalog = json.loads((ROOT / "sources/hanfeizi/catalog.json").read_text(encoding="utf8"))
    pages, sources, options = [], {}, {}
    translated = 0
    volume = 0
    for chapter in catalog:
        if chapter["volume"] != volume:
            volume = chapter["volume"]
            pages.append((None, "卷" + cn(volume)))
        slug = chapter["slug"]
        pages.append((slug, chapter["title"]))
        files = sorted((SRC / "hanfeizi" / slug).glob("*.txt"))
        chunks = [line for f in files for line in f.read_text(encoding="utf8").splitlines()
                  if line.startswith("原：")]
        count = sum(bool(line.partition("||")[2].strip()) for line in chunks)
        if chunks and count == len(chunks):
            translated += 1
        if count:
            options[slug] = {
                "no_tip": False,
                "reading_hint": "",
                "footer": "白话译文为编者自撰，仅供辅助阅读。",
            }
        sources[slug] = {"url": "https://www.gutenberg.org/ebooks/24049", "label": "古登堡计划"}
    return {"title": "韩非子", "author": "［战国］韩非（旧题）",
            "prose": True, "no_tip": True, "original_only": True, "home_intro_own": True,
            "no_count": True, "side_toc": True, "strict_pairs": True, "page_options": options, "pages": pages, "page_sources": sources,
            "reading_hint": "原文直读。",
            "original_footer": "未据影印本逐字校勘。",
            "index_footer": f"全书二十卷、五十五篇，均可阅读原文；已完成白话 {translated}/55 篇。"}


POETRY = {
    "hanfeizi": _hanfeizi_spec(),
    "mozi": _mozi_spec(),
    "zhouli": _zhouli_spec(),
    "guoyu": _guoyu_spec(),
    "xinlun": _xinlun_spec(),
    "yili": _yili_spec(),
    "luoyangjialanji": _luoyangjialanji_spec(),
    "lvshichunqiu": _lvshichunqiu_spec(),
    "fangyan": _fangyan_spec(),
    "wenxuan": _wenxuan_spec(),
    "dadailiji": _dadailiji_spec(),
    "xuanzhenzi": _xuanzhenzi_spec(),
    "dengxizi": _dengxizi_spec(),
    "zhanguoce": _zhanguoce_grouped_spec(),
    "zengguofan": _zengguofan_spec(),
    "classic_list": _classics_spec(),
    "jiayou": _jiayou_spec(),
    "mengxi": _mengxi_spec(),
    "zhenglun-changyan": _zhenglun_changyan_spec(),
    **{slug: _four_classics_spec(slug) for slug in ("xixiangji", "xiyouji", "shuihuzhuan", "sanguoyanyi", "roupotuan")},
    "zuozhuan": _zuozhuan_spec(),
    "zizhitongjian": _zizhitongjian_spec(),
    "guanhanqing": _works_spec("guanhanqing", "关汉卿杂剧", "［元］关汉卿", "折"),
    "zhaoshigu": _works_spec("zhaoshigu", "赵氏孤儿", "［元］纪君祥", "折"),
    "qiannulihun": _works_spec("qiannulihun", "倩女离魂", "［元］郑光祖", "折"),
    "qiangtoumashang": _works_spec("qiangtoumashang", "墙头马上", "［元］白朴", "折"),
    "baiyueting": _works_spec("baiyueting", "拜月亭", "［元］关汉卿", "折"),
    "linlanxiang": {**_works_spec("linlanxiang", "林兰香", "［清］随缘下士", "回"), "center_poems": True, "reading_hint": ""},
    "jinghuayuan": {**_works_spec("jinghuayuan", "镜花缘", "［清］李汝珍", "回"), "center_poems": True, "reading_hint": ""},
    "shenglvqimeng": _works_spec("shenglvqimeng", "声律启蒙", "［清］车万育", "韵", tijie=False, gloss=True),
    "yanzi": _works_spec("yanzi", "晏子春秋", "［春秋］晏婴（后人辑录）", "章", gloss=True, groups=[("内篇（卷一至卷六）", 6), ("外篇（卷七、卷八）", 2)],
                         footer="全书八卷（内篇六卷、外篇两卷）已整理：每章配逐句白话、题解与注释。"),
    "xunzi": _xunzi_spec(),
    "liji": _annotated_selection("liji", "礼记", ""),
    "shangshu": _annotated_selection("shangshu", "尚书",
                                     "整理中。目录底本为维基文库《尚书》；目前仅列已完成注译的篇目。"),
    "zhouyi": _works_spec("zhouyi", "周易", "［先秦］佚名", "节", gloss=True, groups=[("上经（乾至离，三十卦）", 30), ("下经（咸至未济，三十四卦）", 34), ("易传（系辞、说卦、序卦、杂卦）", 5)],
                          footer="六十四卦每卦一页：卦辞、爻辞与彖传、象传（乾坤另有文言传）合在一页，各节逐句白话、题解与注释；易传另列系辞上下、说卦、序卦、杂卦。彖传、象传、文言传已分别入各卦页，故不另设“彖”“大象”“小象”“文言”页。《周易》异说甚多，白话与注释据传统通行解释，分歧处注明“一说”。"),
    "lunyu": _works_spec("lunyu", "论语", "［春秋］孔子弟子及再传弟子", "章", gloss=True,
                         footer="二十篇、五百馀章全部整理：每章配逐句白话、题解与注释。"),
    "mengzi": _works_spec("mengzi", "孟子", "［战国］孟子及其弟子", "章", gloss=True,
                          footer="七篇十四卷、二百六十章全部整理：每章配逐句白话、题解与注释。"),
    "zhuangzi": _works_spec("zhuangzi", "庄子", "［战国］庄周及其后学", "段", gloss=True, groups=[("内篇（七篇）", 7), ("外篇（十五篇）", 15), ("杂篇（十一篇）", 11)],
                            footer="三十三篇全部整理：篇内按维基文库的自然段分节，每段配逐句白话、题解与注释。"),
    "daodejing": _works_spec("daodejing", "道德经", "［春秋］老子（王弼本）", "章", gloss=True,
                             footer="依王弼本，八十一章经文全部整理，每章配逐句白话、题解与注释；王弼注与陆德明《音义》不收。"),
    "donglinghualu": _donglinghualu_spec(),
    "chuanxilu": _chuanxilu_spec(),
    "canying": _canying_spec(),
    "xiaochuang": _xiaochuang_spec(),
    "xianqing": _xianqing_spec(),
    "yuewei": _yuewei_spec(),
    "yantielun": _yantielun_spec(),
    "songlun": _songlun_spec(),
    "huainanzi": _huainanzi_spec(),
    "shangjunshu": _shangjunshu_spec(),
    "liaozhai": _liaozhai_spec(),
    "taohuashan": _plain_novel_spec("taohuashan", "桃花扇", "［清］孔尚任", "出", 44)
        | {"prose": False, "index_footer": ""},
    "mudanting": _mudanting_spec(),
    "hongloumeng": _hongloumeng_spec(),
    "lengyanguan": _plain_novel_spec("lengyanguan", "冷眼观", "［清］王浚卿", "回", 30),
    "jieyuhui": _plain_novel_spec("jieyuhui", "劫余灰", "［清］吴趼人", "回", 16),
    "houguanchang": _plain_novel_spec("houguanchang", "后官场现形记", "［清］许优民", "回", 8),
    "zuijinguanchang": _plain_novel_spec("zuijinguanchang", "最近官场秘密史", "［清］陆士谔", "卷", 32),
    "jinshehui": _plain_novel_spec("jinshehui", "近世社会龌龊史", "［清］吴趼人", "回", 20),
    "ershinian": _sanyan_spec("ershinian", "二十年目睹之怪现状") | {"author": "［清］吴趼人", "unit": "回"},
    "yushimingyan": _sanyan_spec("yushimingyan", "喻世明言"),
    "jingshitongyan": _sanyan_spec("jingshitongyan", "警世通言"),
    "xingshihengyan": _sanyan_spec("xingshihengyan", "醒世恒言"),
    "laocanyouji": _laocanyouji_spec(),
    "laocanyoujixuji": _laocanyoujixuji_spec(),
    "jinpingmei": _jinpingmei_spec(),
    "rulinwaishi": _rulinwaishi_spec(),
    "niehaihua": _plain_novel_spec("niehaihua", "孽海花", "金松岑、曾朴", "回", 35),
    "shangjie": _plain_novel_spec("shangjie", "商界现形记", "［清］云间天赘生", "回", 16),
    "nianzaifanhuameng": {**_plain_novel_spec("nianzaifanhuameng", "廿载繁华梦", "［清］黄世仲", "回", 40),
                          "index_footer": "收序及四十回。"},
    "facaimijue": _plain_novel_spec("facaimijue", "发财秘诀", "［清］吴趼人", "回", 10),
    "fupuxiantan": {**_plain_novel_spec("fupuxiantan", "负曝闲谈", "［清］欧阳巨源", "回", 30),
                   "index_footer": "传世三十回，原书未完。"},
    "jiuweigui": _plain_novel_spec("jiuweigui", "九尾龟", "［清］张春帆", "回", 192),
    "guanchang": _plain_novel_spec("guanchang", "官场现形记", "［清］李宝嘉、欧阳巨源", "回", 60),
    "chuke": _plain_novel_spec("chuke", "初刻拍案惊奇", "［明］凌濛初", "卷", 40),
    "erke": _plain_novel_spec("erke", "二刻拍案惊奇", "［明］凌濛初", "卷", 40),
    "shiji": {"title": "史记", "author": "［西汉］司马迁", "unit": "节",
              "intro": "",
              "pages": _shiji_pages()},
    "shishuo": {"title": "世说新语", "author": "［南朝宋］刘义庆", "unit": "则",
                "intro": "",
                "pages": SHISHUO_PAGES, "page_sources": {"xu": _xu_source("shishuo")}},
    "guwenguanzhi": {"title": "古文观止", "author": "［清］吴楚材、吴调侯 选编", "unit": "篇",
                     "intro": "",
                     "pages": GUWEN_PAGES,
                     "page_sources": {"xu": _xu_source("guwenguanzhi")}},
    "chuci": {"title": "楚辞", "author": "［战国］屈原等", "intro": "", "pages": CHUCI_PAGES},
    "shijing": {"title": "诗经", "author": "［先秦］佚名",
                "intro": "",
                "pages": SHIJING_PAGES, "page_sources": {"xu": _xu_source("shijing")}},
}
# 首页卡片上的书籍简介：只写书本身。各书目录页的简介若维基文库书名页标题下有介绍，则用 sources/wiki_intros.json 里的原文（已转简体）。
BOOK_INTRO = {
    "hanfeizi": "战国法家著作，共五十五篇，以政论、辩难和寓言讨论法令、用人、赏罚与君主权力。",
    "dengxizi": "旧题春秋郑人邓析所撰，今本有《无厚》《转辞》两篇，讨论名实、法令、用人和辩说。",
    "xuanzhenzi": "唐代张志和的道家著作。今存《外篇》三卷，以寓言和问答探讨天地造化、有无与万物变化。",
    "dadailiji": "西汉戴德传辑的礼学文献，兼收孔门问答、曾子论孝、诸侯礼仪及记述物候农事的《夏小正》。",
    "lvshichunqiu": "战国末年吕不韦组织门客编撰的著作，分十二纪、八览、六论，汇集诸家关于治国、修身、农事和礼乐的论说。",
    "wenxuan": "南朝梁昭明太子萧统主持编选的诗文总集，选录先秦至梁的赋、诗、骚、各体文章，分六十卷；本站所据为李善注本，只录正文。",
    "fangyan": "西汉扬雄所作汉语方言词汇书，十三卷，按词义分条，说明同一事物或概念在各地的不同叫法；旧题晋郭璞注。",
    "luoyangjialanji": "杨衒之追记北魏洛阳佛寺的兴废，按城内及城外四方分卷，也记录都城风物、人物掌故和西域见闻。",
    "yili": "先秦礼仪典籍，共十七篇，详述士大夫的冠婚、相见、乡饮、射礼、朝聘、丧服与祭祀。",
    "xinlun": "桓谭论时政、经学与养生的著作，兼谈文章和琴道；原书已佚，今见各书征引辑成的残篇。",
    "guoyu": "先秦国别史，分记周、鲁、齐、晋、郑、楚、吴、越八国言论和史事，以君臣问答与劝谏见长。",
    "zhouli": "旧称《周官》，按六官编排职官与礼制，涉及赋役、祭祀、军政和刑狱；今本以《考工记》补冬官。",
    "mozi": "先秦墨家著作，主张兼爱、非攻、尚贤、节用，也讨论名辩、认识与守城技术。",
    "rongzhai": "南宋洪迈所著的读书笔记，历时近四十年写成，分“五笔”，共七十四卷。内容涉及经史、诗文、典制、考据、掌故，是宋代笔记中的名著。",
    "zhanguoce": "西汉刘向编订的国别体史书，记载战国时期游说之士的谋略与辞令，涉及西周、东周及秦、齐、楚、赵、魏、韩、燕、宋、卫、中山诸国，共三十三卷。",
    "zengguofan": "清代曾国藩写给父母、兄弟、子侄和妻子的家信，涉及治学、修身与齐家，是了解曾国藩思想与晚清士大夫家教的重要材料。",
    "jiayou": "《嘉祐集》是北宋苏洵的文集。苏洵字明允，眉州眉山人，与苏轼、苏辙并称三苏。书中既有《权书》《衡论》一类讨论用兵与治国的文章，也有经解、史论、书札、族谱、杂文和诗。所选底本分十六卷，另有补遗，可从中看见苏洵怎样以古事论当世，又怎样把家族与交游写入文章。",
    "classic_list": "历代散文、辞赋、诗歌名篇选集，收《报任安书》《出师表》《兰亭集序》《离魂记》《洛神赋》《岳阳楼记》《赤壁赋》《醉翁亭记》《阿房宫赋》《陋室铭》《爱莲说》《永州八记》《湖心亭看雪》等三十三项。",
    "guanhanqing": "元代关汉卿所作杂剧合集，收《窦娥冤》《救风尘》《望江亭》《单刀会》《拜月亭》《调风月》等十八种，题材涉及冤狱、婚恋、公案与历史英雄。",
    "zhaoshigu": "元代纪君祥所作杂剧，全称《冤报冤赵氏孤儿》，写程婴、公孙杵臼舍命救护赵氏孤儿、孤儿长大后报仇雪冤的故事。",
    "qiannulihun": "元代郑光祖所作杂剧，全称《迷青琐倩女离魂》，写倩女魂魄离体追随情人王文举、与病中之身终得合一的故事。元代四大爱情剧之一。",
    "qiangtoumashang": "元代白朴所作杂剧，全称《裴少俊墙头马上》，写李千金与裴少俊墙头相见、私奔成婚，历经波折而团圆的故事。元代四大爱情剧之一。",
    "baiyueting": "元代关汉卿所作杂剧，全称《闺怨佳人拜月亭》，写金末兵乱中蒋世隆与王瑞兰患难相识、几经离合而团圆的故事。元代四大爱情剧之一。",
    "jinghuayuan": "清代李汝珍所作长篇小说，全一百回：前半写唐敖、多九公、林之洋出海游历，历君子国、大人国、女儿国等诸国；后半写武则天开女科、百位才女应试及宴游、论学、斗艺的故事。",
    "linlanxiang": "清代世情小说，全书六十四回，旧本题“随缘下士编辑”，以明代耿朗一家妻妾的悲欢为中心，细写家庭日常与人情世态。",
    "yanzi": "记春秋时齐国名相晏婴言行的书，旧题晏婴撰，一般认为是后人采集编成。全书八卷，以晏子劝谏景公、折冲外交、处世节俭而著称，保存了不少先秦轶事；八卷现已全部整理。",
    "liji": "《礼记》是儒家礼学文献的汇编，记述礼仪制度，也讨论修身、教育与治国。",
    "xunzi": "战国儒家文集，讨论学习、人性和治国，强调通过师法与礼义培养德行、建立秩序。",
    "shangshu": "《尚书》汇集虞、夏、商、周的典谟、训诰和誓命，记录早期中国的政治观念与历史传说。",
    "zhouyi": "儒家群经之首，包括经（六十四卦的卦辞、爻辞）和传（彖、象、系辞、文言、说卦、序卦、杂卦等“十翼”）两部分，借阴阳爻象推演吉凶变化，是中国古代哲学与占筮之书。",
    "lunyu": "记孔子及其弟子言行的语录体著作，儒家最基本的经典之一，今本二十篇、五百馀章，后与《孟子》《大学》《中庸》合称“四书”。",
    "mengzi": "记战国中期孟子言行的著作，以问答与辩论为主，主张性善、仁政与王道，七篇十四卷，列入“四书”。",
    "zhuangzi": "战国庄周及其后学的著作，旧称《南华真经》，分内、外、杂三篇共三十三篇，以寓言说理，想象奇诡，是道家的重要典籍。",
    "daodejing": "又称《老子》，道家最重要的经典，五千言分《道经》《德经》，通行八十一章；这里依王弼本整理经文。",
    "shenglvqimeng": "清代车万育编的蒙学读物，按平水韵分三十个韵部，以对句训练对仗与声律，涉及天文、地理、人物与典故。",
    "mengxi": "北宋沈括所著笔记，含《笔谈》二十六卷及《补笔谈》《续笔谈》，涉及天文历法、数学、地理、医药、工艺、艺文、官政与朝野轶事。",
    "zhenglun-changyan": "东汉两部政论著作合编，分别为崔寔《政论》与仲长统《昌言》，议论时政得失、田制、刑法与吏治。原书多佚，今存为后人辑本。",
    "xixiangji": "元杂剧，全称《崔莺莺待月西厢记》，通行五本二十一折并楔子，写张生与崔莺莺在红娘帮助下冲破礼教、自主成婚的故事。元代四大爱情剧之一。",
    "xiyouji": "神魔章回小说，全一百回，通行署吴承恩。写孙悟空出世、大闹天宫及唐僧师徒西行取经、历经八十一难的故事。",
    "shuihuzhuan": "写北宋末年梁山好汉聚义、招安与征战的章回小说，通行署施耐庵，全书一百二十回。",
    "sanguoyanyi": "历史演义小说，写东汉末年至西晋统一的兴亡，通行为罗贯中著、毛宗岗父子评改的一百二十回本。",
    "roupotuan": "清初艳情小说，又名《觉后禅》，全二十回。以因果劝惩为框架，写书生未央生纵欲与报应的经过；含露骨的成人内容，历代屡遭禁毁。",
    "zuozhuan": "先秦编年体史书，依《春秋》经文纪年，记鲁隐公元年至哀公二十七年（前722—前468）及附记之事，是春秋历史叙事与辞令的代表。",
    "zizhitongjian": "宋司马光主编的编年体通史，记战国（前403年）至五代后周（959年），共二百九十四卷、十六纪。",
    "donglinghualu": "南宋孟元老追忆北宋徽宗时东京汴梁城坊、官署、节令、风俗、饮食与游乐的笔记，共十卷。",
    "chuanxilu": "王阳明与弟子问答、论学书信的汇编，分上、中、下三卷，集中阐述“心即理”“知行合一”“致良知”等心学要旨。",
    "canying": "清末民初况周颐的笔记，涉及典章、科举、人物、诗词与金石。",
    "xiaochuang": "又名《醉古堂剑扫》，清言小品集，共十二卷：集醒、集情、集峭、集灵、集素、集景、集韵、集奇、集绮、集豪、集法、集倩。",
    "xianqing": "清代李渔所著戏曲与生活艺术论著，分词曲、演习、声容、居室、器玩、饮馔、种植、颐养八部。",
    "yuewei": "清代纪昀所著文言笔记小说，含《滦阳消夏录》《如是我闻》《槐西杂志》《姑妄听之》《滦阳续录》五种，共二十四卷。",
    "yantielun": "记述汉昭帝始元六年盐铁会议的政论著作，共十卷六十篇。",
    "songlun": "明末清初王夫之评论宋代政治得失的史论，共十五卷。",
    "huainanzi": "西汉淮南王刘安及其门客所著的杂家著作，兼取道、儒、法、阴阳诸家，共二十一卷。",
    "shangjunshu": "法家著作，又名《商子》，讨论变法、耕战、赏刑与法令，今存二十四篇。",
    "liaozhai": "清代蒲松龄所著文言短篇小说集，多写狐鬼花妖，反映世态人情。",
    "taohuashan": "孔尚任的清代传奇，借李香君与侯方域的离合，写南明兴亡与秦淮旧事。",
    "mudanting": "明代汤显祖所作传奇，又名《还魂记》，全五十五出，写杜丽娘因梦生情、因情而死、又因情复生的故事。",
    "niehaihua": "金松岑开篇、曾朴续写的晚清小说，借金雯青与傅彩云的经历，写士林交游、出使见闻与政局变迁。",
    "shangjie": "清末章回小说，围绕商号经营、同业往来和市场风波，描写商场中的利害与人情。",
    "nianzaifanhuameng": "黄世仲的章回小说，以周氏一家的发迹和败落为主线，写晚清广东官商往来与富贵人家的冷暖。",
    "facaimijue": "吴趼人的晚清小说，又名《黄奴外史》，从香港开埠后的营生写起，讽刺逐利和投机发财的种种手段。",
    "fupuxiantan": "欧阳巨源的晚清小说，以科场、衙门和市井里的故事揭露钻营与欺诈，现存三十回。",
    "jiuweigui": "晚清张春帆的长篇小说，以章秋谷的交游为线索，写上海及江南的风月场、市井往来和官商百态。",
    "guanchang": "晚清谴责小说，以一桩桩官场见闻串起六十回，写钻营求官、买缺卖官和上下官员之间的倾轧。",
    "chuke": "明代凌濛初的白话短篇小说集，写商旅、婚姻、诉讼与奇遇，从市井故事中见人情世态。",
    "erke": "凌濛初继《初刻拍案惊奇》之后编撰的白话小说集，多写民间婚恋、商贾往来和公案，末卷另收杂剧。",
    "rulinwaishi": "清代吴敬梓的长篇讽刺小说，写范进、匡超人等读书人的遭际，揭示科举功名怎样左右士人的生活与交往。",
    "jinpingmei": "明代长篇世情小说，以西门庆一家的兴衰为主线，描绘市井生意、家庭日常和官场往来。此处收录崇祯本。",
    "laocanyoujixuji": "刘鹗续写老残的游历，由泰山访道写到梦游阴司，借见闻与异境谈修行、因果和人情。",
    "lengyanguan": "王浚卿的晚清小说，从游宦见闻写到地方衙门和上海洋场，讥刺官场积弊与世态人情。",
    "jieyuhui": "吴趼人的晚清小说，写朱婉贞和陈耕伯的离合，也写海外华工的困苦。",
    "houguanchang": "许优民续写《官场现形记》，借捐输、谋缺等官场故事揭露弊端，也议论农工商的兴衰。",
    "zuijinguanchang": "陆士谔的晚清小说，从赴汉口的轮船上说起，写谋差、钻营和衙门里的人情交易。",
    "jinshehui": "吴趼人接续《二十年目睹之怪现状》，写余有声重到上海后遇见的借贷、招股和买卖官缺等骗局。",
    "ershinian": "吴趼人的晚清小说，借九死一生的二十年见闻，写官场、商界与家庭里的荒唐事。",
    "yushimingyan": "冯梦龙编选的四十篇白话短篇小说，写商旅、婚姻、交友与公案，收有《蒋兴哥重会珍珠衫》《金玉奴棒打薄情郎》等篇。",
    "jingshitongyan": "冯梦龙编选的四十篇白话短篇小说，从伯牙知音写到白娘子、杜十娘，兼收市井故事与传奇。",
    "xingshihengyan": "冯梦龙编选的四十篇白话短篇小说，写寻常人家的情义和命运，也收《卖油郎独占花魁》《十五贯戏言成巧祸》等名篇。",
    "laocanyouji": "刘鹗的晚清小说，以游医老残在山东的见闻串起济南风物、黄河水患与官府冤狱。",
    "hongloumeng": "中国古典长篇小说的巅峰，全一百二十回，写贾、史、王、薛四大家族的兴衰与宝黛爱情悲剧。",
    "shiji": "西汉司马迁所著的第一部纪传体通史，分本纪、表、书、世家、列传，共一百三十卷。",
    "shishuo": "记述东汉末至东晋名士言行的笔记小说，分德行、言语、政事、文学等三十六门，一千余则，语言隽永，是魏晋风度的代表读物。",
    "guwenguanzhi": "清人选编的古文选本，自先秦至明代共二百二十二篇，分十二卷，为古文入门的经典读本。",
    "chuci": "战国楚人屈原及其后学的辞赋总集，由西汉刘向辑成，东汉王逸作注。",
    "shijing": "中国最早的诗歌总集，分风、雅、颂三部分。国风收十五国风土歌谣一百六十首；小雅、大雅为朝廷宴飨、朝会之乐；颂为宗庙祭祀之乐。",
}
for _slug in ("liji", "shangshu", "xunzi"):
    POETRY[_slug]["home_intro_own"] = True

WIKI_INTRO = json.loads((ROOT / "sources/wiki_intros.json").read_text(encoding="utf8"))
assert set(BOOK_INTRO) == set(POETRY) | {b["slug"] for b in BOOKS}, set(BOOK_INTRO) ^ (set(POETRY) | {b["slug"] for b in BOOKS})
for _b in BOOKS:
    _b["intro"] = BOOK_INTRO[_b["slug"]]
for _k, _v in POETRY.items():
    _v["intro"] = WIKI_INTRO[_k]["text"] if WIKI_INTRO.get(_k, {}).get("verbatim") and not _v.get("home_intro_own") else BOOK_INTRO[_k]


TIJIE_LINKS = {"zhouyi": [("在线占卜", "https://tongchen779.github.io/Yi-Ching/")]}


def intro_html(slug):
    """目录页简介：维基文库标题下有介绍则用之，否则同首页简介；按换行分段。"""
    text = WIKI_INTRO.get(slug, {}).get("text") or BOOK_INTRO[slug]
    out = "".join(f'<p class="intro">{esc(x)}</p>' for x in text.split("\n") if x.strip())
    # 全书题解（src/<slug>/tijie）不另立页面，接在简介之后，每段以“主题。”领起
    path = ROOT / "src" / slug / "tijie" / "01.txt"
    if path.exists():
        for para in parse_poems([path])[0]["intro"]:
            head, sep, rest = para.partition("。")
            out += f'<p class="intro tijie"><strong>{esc(head)}{sep}</strong>{esc(rest)}</p>'
    for label, url in TIJIE_LINKS.get(slug, []):
        out += f'<p class="intro tijie"><strong>{esc(label)}：</strong><a href="{esc(url)}">{esc(url)}</a></p>'
    return out


CIRC = re.compile(r"([\u2460-\u2473\u3251-\u325f]+)")


def ed_html(h, state):
    """〈…〉是编者夹注：包进 .ed（小字灰色）；夹注跨句时在每句内各自闭合、续开。state 是长度 1 的列表，记录是否仍在夹注内。"""
    if "〈" not in h and "〉" not in h and not state[0]:
        return h
    out = ['<span class="ed">'] if state[0] else []
    for c in h:
        if c == "〈":
            out.append('<span class="ed">〈'); state[0] = True
        elif c == "〉" and state[0]:
            out.append("〉</span>"); state[0] = False
        else:
            out.append(c)
    if state[0]:
        out.append("</span>")
    return "".join(out)


def poem_orig(text):
    out = []
    for i, part in enumerate(CIRC.split(esc(text))):
        out.append(f"<sup>{part}</sup>" if i % 2 else part.replace("/", "<br>"))
    return "".join(out)


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
                if "||" in ln:
                    o, t = (x.strip() for x in ln[2:].split("||", 1))
                else:
                    o, t = ln[2:].strip(), None
                cur["chunks"].append({"o": o, "t": t, "notes": []})
            elif ln.startswith("诗："):
                cur["chunks"].append({"o": ln[2:].strip(), "t": None, "verse": True, "notes": []})
            elif ln.startswith("图题："):
                cur["chunks"].append({"o": ln[3:], "t": None, "diagram": True, "notes": []})
            elif ln.startswith("图行："):
                last = cur["chunks"][-1]
                assert last.get("diagram"), (path, "图行没有图题")
                last["o"] += "\n" + ln[3:]
            elif ln.startswith("表题："):
                cur["chunks"].append({"tbl": {"cap": ln[3:].strip(), "head": None, "rows": []}, "notes": []})
            elif ln.startswith("表头："):
                last = cur["chunks"][-1] if cur["chunks"] else None
                if last and "tbl" in last and last["tbl"]["head"] is None and not last["tbl"]["rows"]:
                    last["tbl"]["head"] = ln[3:].split("｜")
                else:
                    cur["chunks"].append({"tbl": {"cap": "", "head": ln[3:].split("｜"), "rows": []}, "notes": []})
            elif ln.startswith("表行："):
                tbls = [c for c in cur["chunks"] if "tbl" in c]
                tbls[-1]["tbl"]["rows"].append(ln[3:].split("｜"))
            elif ln.startswith("注："):
                cur["chunks"][-1]["notes"].extend(split_notes(ln[2:].strip()))
            else:
                raise ValueError(f"{path}: 无法解析：{ln}")
    return sections


DRAMA = re.compile(r"(〔[^〕]*〕|【[^】]*】)")
STAGE_BOOKS = {"xixiangji", "taohuashan", "qiangtoumashang", "baiyueting", "qiannulihun", "guanhanqing"}
PEACH_DRAMA = re.compile(r"(〔[^〕]*〕|【[^】]*】|\([^()]*\)|（[^（）]*）)")
ERKE_STAGE = re.compile(r"(〈（[^〉]*）〉|〔[^〕]*〕|【[^】]*】)")
PEACH_TUNES = {"鹧鸪天", "皂罗袍"}
WESTERN_STAGE = re.compile(r"扮|科|(?:云|唱|下|上|上开|上去|念|念曰|白|了|坐|叫|起发)$")
WESTERN_STAGE_EXTRA = {"洁叫了，住", "红见仆人", "见夫人", "歌曰"}


def _verse_like(o):
    return len(o) >= 8 and "“" not in o and "”" not in o and all(len(x) <= 9 for x in re.split(r"[，。！？；、]", o))


def _lyric_like(o):
    """曲词：分句平均不超过 9 字。"""
    parts = [x for x in re.split(r"[，。！？；、]", o) if x]
    return len(o) >= 8 and len(parts) >= 3 and sum(map(len, parts)) / len(parts) <= 9


def is_poem(o, prev, prev_poem=False, nxt=""):
    """红楼梦等：诗词曲联在原文里没有单独标记。以“/”分行的短行段落，紧接在“念道：”“联云：”“正是：”等引语之后的无引号短段，
    紧接在诗行之后的无引号短段，以及曲牌名（短标题，后面紧跟曲词），视为诗歌（含对联、曲），页面居中。“下回分解”之类的回末套语不算。"""
    segs = o.split("/")
    if len(segs) > 1:
        if "下回" in o or re.search(r"[道曰笑说][：:]“", o):
            return False
        return max(len(re.sub(r"\s*[—―]+.*$", "", x)) for x in segs) <= 40
    if len(o) <= 10 and not re.search(r"[，。！？；：“”、]", o) and nxt and "/" not in nxt and _lyric_like(nxt):
        return True    # 曲牌名
    if prev_poem and len(o) <= 200 and not re.search(r"却说|且说|话说|看官|只见|当下", o) and _lyric_like(o) and len(prev) <= 10 and not re.search(r"[，。！？；：“”、]", prev):
        return True    # 曲牌名之后的曲词
    if len(o) >= 60 or "“" in o or "”" in o or "下回" in o or "且听" in o:
        return False
    if prev and re.search(r"(诗|词|曰|云|歌|赞|联|道|是|如|念|唱)[：:—]+$", prev):
        return True
    return prev_poem and bool(re.search(r"[，。！？；]$", o)) and all(len(x) in (5, 7) or "兮" in x for x in re.split(r"[，。！？；]", o) if x)


def _verse_seg(x):
    return (len(x) <= 40 and re.search(r"[，。！？；]$", x) and not re.search(r"[“”‘’「」『』：]", x)
            and "下回" not in x and all(4 <= len(y) <= 9 for y in re.split(r"[，。！？；]", x) if y))


def split_poem_runs(o):
    """正文里夹着的整行诗（连续两行以上，如回首诗、回末对联）：返回 [(是否诗, 文本), ...]；没有则 None。"""
    segs = o.split("/")
    flags = [bool(_verse_seg(x)) for x in segs]
    out, i = [], 0
    while i < len(segs):
        j = i
        while j < len(segs) and flags[j] == flags[i]:
            j += 1
        out.append([flags[i] and j - i >= 2, "/".join(segs[i:j])])
        i = j
    merged = []
    for isp, t in out:
        if merged and merged[-1][0] == isp:
            merged[-1][1] += "/" + t
        else:
            merged.append([isp, t])
    return merged if any(m[0] for m in merged) and len(merged) > 1 else None


def drama_html(text, stage_book=None):
    out = []
    pattern = {"taohuashan": PEACH_DRAMA, "erke": ERKE_STAGE}.get(stage_book, DRAMA)
    for i, part in enumerate(pattern.split(text)):
        if i % 2:
            label = part[1:-1].strip()
            tune = part.startswith("【") or (stage_book == "erke" and part.startswith("〔"))
            if stage_book == "xixiangji" and tune:
                tune = not (WESTERN_STAGE.search(label) or label in WESTERN_STAGE_EXTRA)
            elif stage_book == "taohuashan":
                tune = tune or label in PEACH_TUNES or bool(re.fullmatch(r"鼓词[一二三四五六七八九十]+", label))
            cls = "cp" if tune else "sd"
            label_html = esc(part).replace("/", "<br>") if stage_book else esc(part)
            out.append(f'<span class="{cls}">{label_html}</span>')
        else:
            out.append(esc(part).replace("/", "<br>"))
    return "".join(out)


def table_html(t):
    def cell(tag, c):
        return f"<{tag}>" + "<br>".join(esc(x) for x in c.split("／")) + f"</{tag}>"
    head = ""
    if t["head"]:
        head = "<thead><tr>" + "".join(cell("th", c) for c in t["head"]) + "</tr></thead>"
    body = "".join("<tr>" + "".join(cell("td", c) for c in r) + "</tr>" for r in t["rows"])
    cap = f"<h4 class=\"tcap\">{esc(t['cap'])}</h4>" if t["cap"] else ""
    return f'{cap}<div class="biao-wrap"><table class="biao{" biao-n" if len(t["rows"][0] if t["rows"] else []) >= 10 else ""}">{head}<tbody>{body}</tbody></table></div>'


def build_poetry(bslug, spec):
    r = "../"
    base = SRC / bslug
    btitle = spec["title"]
    pages = []
    for slug, title in spec["pages"]:
        if slug is None:
            pages.append((None, title, []))
            continue
        files = sorted((base / slug).glob("*.txt")) if (base / slug).exists() else []
        pages.append((slug, title, files))
    avail = [i for i, (_, _, f) in enumerate(pages) if f]
    cells, total = [], 0
    for i, (slug, title, files) in enumerate(pages):
        if slug is None:
            wide = ' style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))"' if spec.get("wide_index") else ""
            cells.append(f'</ul><h3 class="grp">{esc(title)}</h3><ul class="vols"{wide}>')
            continue
        if not files:
            status = "阙" if slug in spec.get("missing_slugs", ()) else "待整理"
            cells.append(f'<li class="todo"><span>{esc(title)}<small>{status}</small></span></li>')
            continue
        secs = parse_poems(files)
        stage_book = bslug if bslug in STAGE_BOOKS and (bslug != "taohuashan" or slug.startswith("p")) else None
        if (bslug, slug) == ("erke", "040"):
            stage_book = bslug
        paragraph_style = "dr" if stage_book or not spec.get("prose") else "nv"
        nchunk = sum(1 for s in secs for c in s["chunks"] if "tbl" not in c)
        total += len(secs) if spec.get("count_entries") else nchunk
        cnt = (spec["count"](secs) if "count" in spec else
               (None if spec.get("no_count") else (len(secs), spec.get("unit2", spec.get("unit", "节")))))
        small = f"<small>{cnt[0]}{cnt[1]}</small>" if cnt and cnt[0] > 1 else ""
        index_label = spec.get("page_options", {}).get(slug, {}).get("index_label")
        if index_label:
            small = f"<small>{esc(index_label)}</small>"
        cells.append(f'<li class="ok"><a href="{slug}.html">{esc(title)}{small}</a></li>')
        uid = 0
        body_secs = []
        for si, sec in enumerate(secs, 1):
            parts = [f'<section class="entry" id="e{si}">']
            multi = len(secs) > 1
            parts.append(f'<h3>{esc(sec["title"])}</h3>' if multi and sec["title"] != title else "")
            entry_source = spec.get("section_sources", {}).get(slug, {}).get(sec["title"])
            if entry_source:
                label = esc(entry_source.get("label", "维基文库"))
                revision = entry_source.get("revision")
                version = f"（修订版本 {esc(revision)}）" if revision else ""
                credit = f'；原文据<a href="{esc(entry_source["url"])}">{label}</a>{version}'
                if is_wiki_source(entry_source["url"]):
                    credit = f'<span hidden>{credit}</span>'
                parts.append(f'<p class="hint source-note">原署／材料归属：{esc(entry_source["author"])}{credit}。</p>')
            if sec["intro"]:
                uid += 1
                items = "".join(f"<p>{esc(x)}</p>" for x in sec["intro"])
                parts.append(
                    f'<button class="note-btn" type="button" aria-expanded="false" aria-controls="n{uid}">'
                    f'<span class="caret">▸</span> 题解</button><div class="notes intro-box" id="n{uid}" hidden>{items}</div>')
            prev_o, prev_poem = "", False
            ed_state = [False]
            chunks_ = sec["chunks"]
            for ci, ch in enumerate(chunks_):
                if "tbl" in ch:
                    parts.append(table_html(ch["tbl"]))
                    continue
                if ch.get("diagram"):
                    parts.append(f'<pre class="source-diagram" style="max-width:100%;overflow-x:auto">{esc(ch["o"])}</pre>')
                    continue
                is_p = ch.get("verse") or bool(spec.get("center_poems") and ch["t"] is None and is_poem(ch["o"], prev_o, prev_poem, chunks_[ci + 1]["o"] if ci + 1 < len(chunks_) and "o" in chunks_[ci + 1] else ""))
                poem = " poem" if is_p else ""
                prev_o, prev_poem = ch["o"], is_p
                if ch["t"] is None:
                    runs = split_poem_runs(ch["o"]) if spec.get("center_poems") and not poem else None
                    if runs:
                        for isp, txt in runs:
                            parts.append(f'<p class="v {paragraph_style}{" poem" if isp else ""}">{drama_html(txt, stage_book)}</p>')
                    else:
                        parts.append(f'<p class="v {paragraph_style}{poem}">{drama_html(ch["o"], stage_book)}</p>')
                else:
                  spans = ""
                  pairs = split_pairs(ch["o"], ch["t"])
                  if spec.get("unaligned_translation_details") and not has_sentence_pairs(ch):
                      parts.append(f'<p class="v nv">{drama_html(ch["o"])}</p>'
                                   f'<details class="translation-draft"><summary>段落白话</summary>'
                                   f'<p>{esc(ch["t"])}</p></details>')
                      pairs = []
                  if spec.get("strict_pairs"):
                      original_sents = split_sents(ch["o"])
                      if (len(original_sents) != len(ch["t"].split("¦"))
                              or [o for o, _t in pairs] != original_sents):
                          raise ValueError(f"{bslug}/{slug}: 原文与白话必须逐句对应，不能整段回退")
                  for o2, t2 in pairs:
                      if o2.startswith("/"):
                          spans += "<br>"
                          o2 = o2[1:]
                      spans += f'<span class="s" tabindex="0" data-t="{esc(t2)}">{ed_html(poem_orig(o2), ed_state)}</span>'
                  if pairs:
                      label = ch["o"].strip() if bslug == "hanfeizi" else ""
                      if label == "右经":
                          parts.append(f'<p class="hf-end-marker">{spans}</p>')
                      elif re.fullmatch(r"说[一二三四五六七八九十]+", label):
                          parts.append(f'<h3 class="hf-example-heading">{spans}</h3>')
                      else:
                          parts.append(f'<p class="v">{spans}</p>')
                if ch["notes"]:
                    uid += 1
                    li = "".join(f"<li>{esc(n)}</li>" for n in ch["notes"])
                    parts.append(
                        f'<button class="note-btn" type="button" aria-expanded="false" aria-controls="n{uid}">'
                        f'<span class="caret">▸</span> 注释（{len(ch["notes"])}）</button><ul class="notes plain" id="n{uid}" hidden>{li}</ul>')
            parts.append("</section>")
            body_secs.append("\n".join(x for x in parts if x))
        toc = ""
        if spec.get("side_toc") and (spec.get("side_toc_always") or
                                    sum(1 for s_ in secs if not (s_["title"] == title and not s_["chunks"])) <= 1):
            items = []
            for sl, tt, page_files in pages:
                if sl is None:
                    items.append(f'<li class="grp">{esc(tt)}</li>')
                elif sl == slug:
                    items.append(f'<li class="cur"><a href="{sl}.html" aria-current="page">{esc(tt)}</a></li>')
                elif page_files:
                    items.append(f'<li><a href="{sl}.html">{esc(tt)}</a></li>')
                else:
                    status = "阙" if sl in spec.get("missing_slugs", ()) else "待整理"
                    items.append(f'<li><span>{esc(tt)}（{status}）</span></li>')
            toc = (f'<details class="toc side" open><summary>总目录</summary><ul>{"".join(items)}</ul></details>')
        elif secs:
            tocs = [(k, s) for k, s in enumerate(secs, 1) if not (s["title"] == title and not s["chunks"])]
            numeric = sum(1 for _k, s in tocs if s["title"].isdigit()) * 2 > len(tocs)
            if numeric:
                toc = ('<details class="toc" open><summary>本页目录</summary><ul class="num">'
                       + "".join(f'<li><a href="#e{k}">{esc(s["title"])}</a></li>' for k, s in tocs)
                       + "</ul></details>")
            else:
                toc = ('<details class="toc" open><summary>本页目录</summary><ol>'
                       + "".join(f'<li><a href="#e{k}">{esc(s["title"])}</a></li>' for k, s in tocs)
                       + "</ol></details>")
        prev_i = max([j for j in avail if j < i], default=None)
        next_i = min([j for j in avail if j > i], default=None)
        prev_h = (f'<a href="{pages[prev_i][0]}.html">← {esc(pages[prev_i][1])}</a>' if prev_i is not None
                  else '<span class="off">&nbsp;</span>')
        next_h = (f'<a href="{pages[next_i][0]}.html">{esc(pages[next_i][1])} →</a>' if next_i is not None
                  else '<span class="off">&nbsp;</span>')
        source = spec.get("page_sources", {}).get(slug)
        page_options = spec.get("page_options", {}).get(slug, {})
        revision_note = f'（修订版本 {esc(source["revision"])}）' if source and source.get("revision") else ""
        source_note = (f'{esc(source.get("prefix", "原文据"))}<a href="{esc(source["url"])}">{esc(source.get("label", "维基文库"))}</a>整理{revision_note}；{esc(source.get("after", ""))}'
                       if source else ("本页题解为编者自撰；" if slug == "tijie" and bslug in ("xixiangji", "xiyouji", "shuihuzhuan", "sanguoyanyi", "roupotuan", "zuozhuan") else "原文依所标明底本整理；"))
        if spec.get("omit_source_credit"):
            source_note = ""
        elif source and is_wiki_source(source["url"]):
            source_note = f'<span hidden>{source_note}</span>'
        if page_options.get("no_tip", spec.get("no_tip")):
            hint = "原文直读，不设悬浮译文。"
            foot_text = "注释为编者自撰，仅供辅助阅读，以原文为准。"
            if spec.get("original_only"):
                hint = "原文阅读版；白话与注释待整理。条目编号为整理者所加。"
                foot_text = spec.get("original_footer", "保留原站校勘记及缺文标记；尚未据影印本逐字校勘。")
        else:
            hint = ""
            foot_text = "白话译文、注释、题解为编者自撰，仅供辅助阅读，以原文为准。"
        hint = page_options.get("reading_hint", spec.get("reading_hint", hint))
        foot_text = page_options.get("footer", foot_text)
        body = f"""<header class="top">
{crumbs([("古典文库", r + "index.html"), (btitle, "index.html"), (title, None)])}
<h1>{esc(title)}<small>{esc(btitle)}</small></h1>
{f'<p class="hint">{hint}</p>' if hint else ""}
</header>
<main class="reading-layout">
{toc}
<div class="reading-content">
{chr(10).join(body_secs)}
<nav class="pager">{prev_h}<a href="index.html">目录</a>{next_h}</nav>
</div>
</main>
<div id="tip" role="tooltip" hidden></div>
<footer>{source_note}{foot_text}</footer>"""
        out = ROOT / bslug / f"{slug}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(f"{title}·{btitle}", body, r, True), encoding="utf8")
    intro_credit = ""
    if WIKI_INTRO.get(bslug, {}).get("verbatim") and not spec.get("omit_source_credit"):
        url = esc(WIKI_INTRO[bslug]["url"])
        visibility = "" if spec.get("visible_intro_credit") else " hidden"
        label = "简介据维基文库" if spec.get("visible_intro_credit") else "维基文库"
        intro_credit = (f'<span{visibility}> · <a href="{url}">{label}</a> · '
                        '<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a></span>')
    body = f"""<header class="top">
{crumbs([("古典文库", "../index.html"), (btitle, None)])}
<h1>{esc(btitle)}<small>{esc(spec["author"])}</small></h1>
{intro_html(bslug)}
</header>
<main><section class="part"><ul class="vols"{' style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))"' if spec.get('wide_index') else ''}>{"".join(cells)}</ul></section></main>
<footer>{esc(spec.get("index_footer", f'已整理 {total} {spec.get("summary_unit", "节")}。'))}{intro_credit}</footer>"""
    (ROOT / bslug).mkdir(parents=True, exist_ok=True)
    (ROOT / bslug / "index.html").write_text(page(btitle, body, "../"), encoding="utf8")
    for old_slug, target in spec.get("page_redirects", {}).items():
        redirect = f'<!doctype html><html lang="zh-Hans"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="0; url={esc(target)}"><link rel="canonical" href="{esc(target)}"><title>{esc(btitle)}·合并阅读</title></head><body><h1>合并阅读</h1><p>本篇已合入统一阅读页：<a href="{esc(target)}">打开本篇</a></p></body></html>'
        (ROOT / bslug / (old_slug + ".html")).write_text(redirect, encoding="utf8")
    return total


# 书名首字的拼音首字母，供首页字母索引使用；新增书目若首字不在表内，build 会报错提醒补充。
INITIAL = dict(zip("容战曾经梦政西水三肉春资餐小闲阅盐宋淮商聊牡红史世古楚诗东传关赵倩墙拜林声镜晏周论孟庄道礼尚嘉墨",
                   "RZCJMZXSSRCZCXXYYSHSLMHSSGCSDCGZQQBLSJYZLMZDLSJM"))


INITIAL["荀"] = "X"
INITIAL["老"] = "L"
INITIAL["桃"] = "T"
INITIAL["国"] = "G"
INITIAL["新"] = "X"
INITIAL.update({"冷": "L", "劫": "J", "后": "H", "最": "Z", "近": "J"})
INITIAL.update({"喻": "Y", "警": "J", "醒": "X"})
INITIAL["玄"] = "X"
INITIAL["邓"] = "D"
INITIAL["大"] = "D"
INITIAL["韩"] = "H"
INITIAL["仪"] = "Y"
INITIAL["洛"] = "L"
INITIAL["吕"] = "L"
INITIAL["方"] = "F"
INITIAL["昭"] = "Z"
INITIAL["金"] = "J"
INITIAL["儒"] = "R"
INITIAL.update({"孽": "N", "商": "S", "廿": "N", "发": "F", "负": "F"})
INITIAL.update({"官": "G", "初": "C", "二": "E", "九": "J"})


def build_home():
    def card(href, b):
        first = b["title"][0]
        assert first in INITIAL, f"首页字母索引缺少“{first}”的拼音首字母（build.py INITIAL）"
        return (f'<li data-letter="{INITIAL[first]}"><a href="{href}/index.html"><strong>{esc(b["title"])}</strong>'
                f'<span>{esc(b["author"])}</span><p>{esc(b["intro"])}</p></a></li>')
    cards = "".join(card(b["slug"], b) for b in BOOKS) + "".join(card(k, v) for k, v in POETRY.items())
    letters = "".join(f'<button type="button" class="letter" data-letter="{c}" aria-pressed="false">{c}</button>'
                      for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    body = f"""<header class="top"><h1>古典文库<small>文言典籍逐句对照白话，白话小说径读原文</small></h1></header>
<main>
<div class="book-search" role="search" aria-label="搜索书籍">
<label for="book-search">搜索书名、作者或简介</label>
<div class="search-row"><input type="search" id="book-search" placeholder="例如：聊斋、王夫之、诗经" autocomplete="off" aria-controls="book-list"><button type="button" id="search-clear">清空</button></div>
<div class="letters" id="letter-bar" role="group" aria-label="按书名首字拼音首字母浏览">{letters}</div>
<p class="search-status" id="search-status" role="status" aria-live="polite"></p>
</div>
<ul class="books" id="book-list">{cards}</ul>
<p class="search-empty" id="search-empty" hidden>没有找到匹配的书籍，请换个关键词。</p>
<script src="assets/search.js" defer></script>
</main>"""
    (ROOT / "index.html").write_text(page("古典文库", body, ""), encoding="utf8")


if __name__ == "__main__":
    for b in BOOKS:
        build_book(b)
    for _k, _v in POETRY.items():
        build_poetry(_k, _v)
    build_home()
    print("done")
