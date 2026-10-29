#!/usr/bin/env python3
"""把 src/ 下的标注文本生成静态网页。用法：python3 build.py"""
import html
import re
from pathlib import Path

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

def _ver(name):
    import hashlib
    return hashlib.md5((ROOT / "assets" / name).read_bytes()).hexdigest()[:8]


CSS_LINK = '<link rel="stylesheet" href="{r}assets/style.css?v=' + "{v}" + '">'


def esc(s):
    return html.escape(s, quote=True)


GLOSS = re.compile(r"(（[^（）]*）|\([^()]*\))")

SENT = re.compile(r"[^。！？]*[。！？]+[”’」』）]*|[^。！？]+$")


def split_sents(s):
    return [x for x in SENT.findall(s) if x.strip()]


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
    """按句号/叹号/问号把一段原文拆成句，并与译文逐句对应。
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
                    if groups and not re.search(r"[\u4e00-\u9fff]", x):
                        groups[-1].append(k)
                    else:
                        groups.append([k])
            return [("".join(raw[k] for k in g), "".join(st[k] for k in g)) for g in groups]
        if len(st) == len(groups):
            return [("".join(raw[k] for k in g), x) for g, x in zip(groups, st)]
    return [(o, t.replace("¦", ""))]


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


def page(title, body, r, extra_js=False):
    js = f'<script src="{r}assets/reader.js?v={_ver("reader.js")}" defer></script>' if extra_js else ""
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{CSS_LINK.format(r=r, v=_ver("style.css"))}
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
    pslug, ptitle, pord, nvol = part
    heading, entries = parse_juan(src_path)
    r = "../../"
    toc = "".join(f'<li><a href="#e{i}">{esc(e["title"])}</a></li>' for i, e in enumerate(entries, 1))
    prev_html = (f'<a href="juan{vol-1:02d}.html">← 卷{cn(vol-1)}</a>' if (vol - 1) in avail
                 else '<span class="off">&nbsp;</span>')
    next_html = (f'<a href="juan{vol+1:02d}.html">卷{cn(vol+1)} →</a>' if (vol + 1) in avail
                 else '<span class="off">下一卷：待整理</span>')
    body = f"""<header class="top">
{crumbs([("古典文库", r + "index.html"), (book["title"], "../index.html"), (ptitle, None)])}
<h1>{esc(ptitle)}<small>{esc(pord)}</small></h1>
<h2>{esc(heading)}</h2>
<p class="hint">鼠标移到原文句子上，即显示白话；点击每则末尾的“注释”可展开补充说明。触屏设备请点按句子。</p>
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
{crumbs([("古典文库", "../index.html"), (book["title"], None)])}
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
SHISHUO_PAGES = [
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
            "intro": "文言短篇小说集，写狐鬼花妖、世态人情。保留中华书局全本全注全译本的十二卷篇序；后续原文改取维基文库，继续逐句配自撰白话、注释与题解。" + status,
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
            "page_sources": {f"juan{v['volume']:02d}": next(e["review"] for e in v["entries"] if e.get("review", {}).get("source") == "wikisource")
                             for v in progress["volumes"] if any(e.get("review", {}).get("source") == "wikisource" for e in v.get("entries", []))},
            "intro": "西汉思想著作，共二十一卷。已完成卷依中华书局陈广忠译注本校录，后续原文改取维基文库，继续配自撰逐句白话、独立注释与题解。"
                     + f"目前已整理{complete}节。" + status + "分节编号及小标题为整理者所加。",
            "pages": [(f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}·{v['title']}" +
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
            "intro": "评论宋代政治得失的史论，共十五卷。已完成卷依中华书局刘韶军译注本校录，后续原文改取维基文库，继续配自撰逐句白话、独立注释与题解。"
                     + f"目前已整理{complete}篇。" + status + "保留原书篇序，篇序后的概括性小标题为整理者所加。",
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
            "intro": "记述汉昭帝始元六年盐铁会议的政论著作，共十卷六十篇。卷一依中华书局陈桐生译注本校录，卷二起原文取维基文库；白话、独立注释与题解均自撰。"
                     + f"目前已整理{complete}篇。" + status,
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
            "intro": "清代文言笔记，含《滦阳消夏录》《如是我闻》《槐西杂志》《姑妄听之》《滦阳续录》五种，共二十四卷。已完成部分依中华书局韩希明译注本校录，后续原文改取维基文库，继续配自撰逐句白话、独立注释与题解。"
                     + f"目前已整理{stories}则正文，另收原序、郑序、自题诗二首、各卷卷首自记及卷二十四附录《纪汝佶六则》。" + status
                     + "原书各则没有篇题，编号与概括标题为整理者所加；目录项数含序、诗与自记。",
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
            "intro": "明代传奇名剧，又名《还魂记》，全五十五出，写杜丽娘因梦生情、因情而死、又因情复生的故事。曲词半文半白，故只录原文，随段附少量注释；卷末附话本《杜丽娘慕色还魂》。",
            "pages": pages}


def _hongloumeng_spec():
    pages = []
    for d in sorted((ROOT / "src/hongloumeng").glob("[0-9][0-9][0-9]")):
        n = int(d.name)
        if (n - 1) % 10 == 0:
            pages.append((None, f"第{cn(n)}回至第{cn(n + 9)}回"))
        head = (d / "01.txt").read_text(encoding="utf8").splitlines()[0][2:].strip()
        no, _, name = head.partition(" ")
        pages.append((d.name, f"{no}·{name}"))
    return {"title": "红楼梦", "author": "［清］曹雪芹、高鹗", "unit": "回", "prose": True, "no_tip": True, "side_toc": True,
            "intro": "中国古典长篇小说的巅峰，全一百二十回，写贾、史、王、薛四大家族的兴衰与宝黛爱情悲剧。据维基文库汇校本（前八十回以庚辰本为底本，后四十回以程甲本为底本，不含批语），转为简体；白话原文直读，不设悬浮。",
            "pages": pages}


def _xianqing_spec():
    import json
    progress = json.loads((ROOT / "sources/xianqing/progress.json").read_text(encoding="utf8"))
    return {"title": "闲情偶寄", "author": "［清］李渔", "unit": "项",
            "count_entries": True, "summary_unit": "项",
            "intro": "清代戏曲与生活艺术论著，八部合为六卷。卷前二序与凡例、卷一《词曲部上》依本地中华书局杜书瀛译注本校录；"
                     "卷二至卷六（词曲部下、演习部、声容部、居室部、器玩部、饮馔部、种植部、颐养部）据维基文库收录，全部配自撰逐句白话、独立注释与题解。"
                     "目录项数含总论与卷前材料，不等于原书款数；《演习部·脱套第五》因维基文库页面误录，改据 Project Gutenberg 电子书。",
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
            "intro": "又名《醉古堂剑扫》，清言小品集，共十二卷：集醒、集情、集峭、集灵、集素、集景、集韵、集奇、集绮、集豪、集法、集倩。据维基文库简体版收录十二卷及引、自叙、凡例，保留原站校勘记与缺文标记。"
                     + f"全书{translated}段均配逐句白话（含卷首署名），共{notes}条编者注释；条目编号为整理者所加。",
            "index_footer": f"原文收录1547段；已配白话与编者注释{translated}段。原站校勘记另列，不计作编者注释。",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_options": {p["slug"]: {"no_tip": False,
                  "reading_hint": "本卷已配逐句白话与独立注释。鼠标悬停或触屏点按原文可看译文；点击注释、题解可展开。卷末另附原站校勘记。",
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
            "intro": "清末民初况周颐的笔记，涉及典章、科举、人物、诗词与金石。据用户选定的中国哲学书电子化计划底本收录全文390段，分13页阅读，保留原站632处夹注。"
                     + status + "原站旧字库缺字逐处标明，不猜补。段号沿用原站，目录标题与题解为编者所加。",
            "index_footer": f"原文收录390段；已配白话、题解与编者注释{len(completed)}段。",
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_options": {p["slug"]: {"no_tip": False,
                  "reading_hint": "鼠标移到原文上显示本句白话，触屏设备请点按原文；点击题解、注释可展开。括号内仍保留底本夹注，疑字、缺字的辨读见注释。",
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
            "count_entries": False,
            **({"count": lambda secs: (sum(1 for s in secs if s["title"].endswith("折")), "折")}
               if slug == "xixiangji" else {"no_count": True}),
            "index_footer": f"正文 {progress['chapter_count']} {meta['unit']}；另收全书题解及所选版本附文。",
            "reading_hint": "原文直读；点击“题解”“注释”可展开。附基础导读注释，不设白话译文。",
            "intro": meta["intro"],
            "pages": [(p["slug"], p["title"]) for p in progress["pages"]],
            "page_sources": {p["slug"]: p["source"] for p in progress["pages"] if "source" in p}}


def _shangjunshu_spec():
    import json
    progress = json.loads((ROOT / "sources/shangjunshu/progress.json").read_text(encoding="utf8"))
    return {"title": "商君书", "author": "［战国］商鞅及后学（旧题商鞅）", "unit": "目",
            "count_entries": True, "summary_unit": "目",
            "intro": "法家著作，又名《商子》，讨论变法、耕战、赏刑与法令。依维基文库五卷本整理，现存24篇正文逐句配自撰白话、题解与独立注释；《刑约》《御盗》两篇保留缺佚说明。传文疑误字保留并注。",
            "index_footer": "五卷26目：24篇现存正文，另2目正文亡佚。",
            "pages": [(f"juan{v['volume']:02d}", f"卷{cn(v['volume'])}") for v in progress["volumes"]],
            "page_sources": {f"juan{v['volume']:02d}": v["source"] for v in progress["volumes"]}}


def _zuozhuan_spec():
    import json
    progress = json.loads((ROOT / "sources/zuozhuan/progress.json").read_text(encoding="utf8"))
    return {"title": "春秋左传", "author": "［春秋］左丘明（相传）", "unit": "年",
            "count_entries": False,
            "count": lambda secs: (len({s["title"].split("·")[0] for s in secs}), "年"),
            "intro": "先秦编年体史书，依《春秋》经文纪年，记鲁隐公元年至哀公二十七年（前722—前468）及附记之事，是春秋历史叙事与辞令的代表。"
                     "据维基文库收录杜预序与十二公全文，逐句配自撰白话，并有题解与词条注释；经、传分条，注释偏重人名地名、礼制与笔法术语。",
            "pages": [("tijie", "全书题解")] + [(p["slug"], p["title"]) for p in progress["pages"]],
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
            "intro": "东汉两部政论著作合目，分别署崔寔《政论》、仲长统《昌言》。原书多佚，据维基文库现存辑本整理，保留引书、异文、阙题与缺佚说明，不补造亡文。" + status,
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
            "intro": "据维基文库通行电子辑录整理，范围含四库提要、作者自序、正文二十六卷、补笔谈三卷和续笔谈十一篇。提要另署清代馆臣，不混用另名版本。" + status,
            "pages": [(p["slug"], p["title"] + (f"（已译{sum(u['status'] == 'complete' for u in p['units'])}/{len(p['units'])}段）"
                       if p.get("annotation_status") == "in_progress" else "")) for p in pages],
            "page_sources": {p["slug"]: p["source"] for p in pages if "source" in p}}


POETRY = {
    "mengxi": _mengxi_spec(),
    "zhenglun-changyan": _zhenglun_changyan_spec(),
    **{slug: _four_classics_spec(slug) for slug in ("xixiangji", "xiyouji", "shuihuzhuan", "sanguoyanyi", "roupotuan")},
    "zuozhuan": _zuozhuan_spec(),
    "canying": _canying_spec(),
    "xiaochuang": _xiaochuang_spec(),
    "xianqing": _xianqing_spec(),
    "yuewei": _yuewei_spec(),
    "yantielun": _yantielun_spec(),
    "songlun": _songlun_spec(),
    "huainanzi": _huainanzi_spec(),
    "shangjunshu": _shangjunshu_spec(),
    "liaozhai": _liaozhai_spec(),
    "mudanting": _mudanting_spec(),
    "hongloumeng": _hongloumeng_spec(),
    "shiji": {"title": "史记", "author": "［西汉］司马迁", "unit": "节",
              "intro": "中国第一部纪传体通史，分本纪、表、书、世家、列传共一百三十卷。此处依《二十四史全译》本，只收原文，十表仅收序言与论赞。",
              "pages": _shiji_pages()},
    "shishuo": {"title": "世说新语", "author": "［南朝宋］刘义庆", "unit": "则",
                "intro": "记述东汉末至东晋名士言行的笔记小说，分德行、言语、政事、文学等三十六门，一千余则，语言隽永，是魏晋风度的代表读物。",
                "pages": SHISHUO_PAGES},
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


def drama_html(text):
    out = []
    for i, part in enumerate(DRAMA.split(esc(text))):
        if i % 2:
            cls = "cp" if part.startswith("【") else "sd"
            out.append(f'<span class="{cls}">{part}</span>')
        else:
            out.append(part.replace("/", "<br>"))
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
            cells.append(f'</ul><h3 class="grp">{esc(title)}</h3><ul class="vols">')
            continue
        if not files:
            cells.append(f'<li class="todo"><span>{esc(title)}<small>待整理</small></span></li>')
            continue
        secs = parse_poems(files)
        nchunk = sum(1 for s in secs for c in s["chunks"] if "tbl" not in c)
        total += len(secs) if spec.get("count_entries") else nchunk
        cnt = (spec["count"](secs) if "count" in spec else
               (None if spec.get("no_count") else (len(secs), spec.get("unit2", spec.get("unit", "节")))))
        small = f"<small>{cnt[0]}{cnt[1]}</small>" if cnt and cnt[0] > 1 else ""
        cells.append(f'<li class="ok"><a href="{slug}.html">{esc(title)}{small}</a></li>')
        uid = 0
        body_secs = []
        for si, sec in enumerate(secs, 1):
            parts = [f'<section class="entry" id="e{si}">']
            multi = len(secs) > 1
            parts.append(f'<h3>{esc(sec["title"])}</h3>' if multi and sec["title"] != title else "")
            if sec["intro"]:
                uid += 1
                items = "".join(f"<p>{esc(x)}</p>" for x in sec["intro"])
                parts.append(
                    f'<button class="note-btn" type="button" aria-expanded="false" aria-controls="n{uid}">'
                    f'<span class="caret">▸</span> 题解</button><div class="notes intro-box" id="n{uid}" hidden>{items}</div>')
            for ch in sec["chunks"]:
                if "tbl" in ch:
                    parts.append(table_html(ch["tbl"]))
                    continue
                if ch["t"] is None:
                    parts.append(f'<p class="v {"nv" if spec.get("prose") else "dr"}">{drama_html(ch["o"])}</p>')
                else:
                  spans = ""
                  for o2, t2 in split_pairs(ch["o"], ch["t"]):
                      if o2.startswith("/"):
                          spans += "<br>"
                          o2 = o2[1:]
                      spans += f'<span class="s" tabindex="0" data-t="{esc(t2)}">{poem_orig(o2)}</span>'
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
        if spec.get("side_toc") and len(secs) <= 1:
            items = []
            for sl, tt, _f in pages:
                if sl is None:
                    items.append(f'<li class="grp">{esc(tt)}</li>')
                elif sl == slug:
                    items.append(f'<li class="cur"><a href="{sl}.html" aria-current="page">{esc(tt)}</a></li>')
                else:
                    items.append(f'<li><a href="{sl}.html">{esc(tt)}</a></li>')
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
        if page_options.get("no_tip", spec.get("no_tip")):
            hint = "原文直读，不设悬浮译文；点击“注释”可展开或收起。"
            foot_text = "注释为编者自撰，仅供辅助阅读，以原文为准。"
            if spec.get("original_only"):
                hint = "原文阅读版；白话与注释待整理。条目编号为整理者所加。"
                foot_text = spec.get("original_footer", "保留原站校勘记及缺文标记；尚未据影印本逐字校勘。")
        else:
            hint = "鼠标移到原文上，即显示白话译文；点击“注释”“题解”可展开或收起。触屏设备请点按原文。"
            foot_text = "白话译文、注释、题解为编者自撰，仅供辅助阅读，以原文为准。"
        hint = page_options.get("reading_hint", spec.get("reading_hint", hint))
        foot_text = page_options.get("footer", foot_text)
        body = f"""<header class="top">
{crumbs([("古典文库", r + "index.html"), (btitle, "index.html"), (title, None)])}
<h1>{esc(title)}<small>{esc(btitle)}</small></h1>
<p class="hint">{hint}</p>
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
    body = f"""<header class="top">
{crumbs([("古典文库", "../index.html"), (btitle, None)])}
<h1>{esc(btitle)}<small>{esc(spec["author"])}</small></h1>
<p class="intro">{esc(spec["intro"])}</p>
</header>
<main><section class="part"><ul class="vols">{"".join(cells)}</ul></section></main>
<footer>{esc(spec.get("index_footer", f'已整理 {total} {spec.get("summary_unit", "节")}。'))}</footer>"""
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
    body = f"""<header class="top"><h1>古典文库<small>文言典籍逐句对照白话，白话小说径读原文</small></h1></header>
<main>
<div class="book-search" role="search" aria-label="搜索书籍">
<label for="book-search">搜索书名、作者或简介</label>
<div class="search-row"><input type="search" id="book-search" placeholder="例如：聊斋、王夫之、诗经" autocomplete="off" aria-controls="book-list"><button type="button" id="search-clear">清空</button></div>
<p class="search-status" id="search-status" role="status" aria-live="polite"></p>
</div>
<ul class="books" id="book-list">{cards}</ul>
<p class="search-empty" id="search-empty" hidden>没有找到匹配的书籍，请换个关键词。</p>
<script src="assets/search.js?v={_ver('search.js')}" defer></script>
</main>"""
    (ROOT / "index.html").write_text(page("古典文库", body, ""), encoding="utf8")


if __name__ == "__main__":
    for b in BOOKS:
        build_book(b)
    for _k, _v in POETRY.items():
        build_poetry(_k, _v)
    build_home()
    print("done")
