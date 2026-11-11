#!/usr/bin/env python3
"""把 sources/shitouji/raw/ 里的维基文库《脂硯齋重評石頭記》wikitext 转成 src/shitouji/<页>/01.txt（站内小说格式）：
  正文照录（繁转简）；脂批 {{~|…}}、{{~~|…}}、编者按 {{*|…}}、小字夹注 <sub>…</sub> 写成〈…〉，站内显示为小字灰色；
  页面脚注 <ref>…</ref> 写成①②…，注释照录（“注原：”）；不做白话、不另行撰写注释。

  python3 tools/prepare_shitouji.py
"""
import json
import re
import sys
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources/shitouji/raw"
OUT = ROOT / "src/shitouji"
cc = OpenCC("t2s")
CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟"
SP = "　"
BOM = "﻿"


def strip_markup(t):
    t = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]]*)\]\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"</?(?:font|center|sub|poem)[^>]*>", "", t)
    t = re.sub(r"<br\s*/?>", "", t)
    return t


def clean_inline(t, notes):
    """处理一个段落里的行内模板与脚注，返回带①标记的文本；notes 收集本段的脚注。"""
    t = re.sub(r"\{\{gap(?:\|[^}]*)?\}\}", SP, t)
    t = re.sub(r"\{\{另\|([^|}]*)\|[^}]*\}\}", r"\1", t)

    def ref(m):
        body = re.sub(r"\[\[(?:File|Image|文件)[^\]]*\]\]", "", re.sub(r"\{\{[^{}]*\}\}", "", m.group(1)))
        body = strip_markup(body)
        body = re.sub(r"\s+", " ", body).strip()
        body = re.sub(r"[，：]\s*。", "。", body)
        if len(notes) >= len(CIRC):
            raise ValueError("脚注超过 35 条")
        notes.append(body)
        return CIRC[len(notes) - 1]

    # 引用同名脚注（自闭合）不单独编号：照录原文位置，用同一序号
    t = re.sub(r"<ref name=[^>]*/>", "", t)
    t = re.sub(r"<ref[^>/]*>(.*?)</ref>", ref, t, flags=re.S)
    # 脂批、按语：模板里可能还有嵌套的 ref（上一步已换成序号），这里只剩纯文本
    t = re.sub(r"<sub>(.*?)</sub>", lambda m: "〈" + m.group(1).strip() + "〉", t, flags=re.S)
    t = re.sub(r"\[\[(?:File|Image|文件)[^\]]*\]\]", "□", t)     # 正文里的缺字图片，站内用 □
    return t


def templates(body):
    """脂批 {{~|…}}、{{~~|…}}、按语 {{*|…}}：写成〈…〉；模板内换行处各行自成一段，分别闭合。由内向外替换（脂批里可能嵌着校异小注）。"""
    body = body.replace("</<br>", "")
    body = re.sub(r"</?br\s*/?>", "<br>", body)
    body = re.sub(r"\{\{gap(?:\|[^}]*)?\}\}", SP, body)
    body = re.sub(r"\{\{另\|([^|}]*)\|[^}]*\}\}", r"\1", body)

    def sub(m):
        inner = re.sub(r"<br\s*/?>", "", m.group(1)).strip()
        return "〈" + re.sub(r"\n\s*", "〉\n〈", inner) + "〉"

    while True:
        new = re.sub(r"\{\{\s*(?:~~|~|\*)\s*\|((?:(?!\{\{|\}\}).)*)\}\}", sub, body, flags=re.S)
        if new == body:
            return body
        body = new


def paragraphs(body):
    """正文拆成 (种类, 文字) 段落：空行分段；诗词（<poem>、{{center|…}}、“::”行、缩进三格以上的行）连续的行并成一段，行间用“/”，种类为 "诗"，其余为 "原"。"""
    body = templates(body)
    body = re.sub(r"\{\{(?:未校訂|Footer|footer|版本合成|Textquality[^}]*)\}\}", "", body)
    body = re.sub(r"<font[^>]*>.*?</font>", "", body, flags=re.S)
    body = re.sub(r"</?center>", "", body)
    body = re.sub(r"<poem>(.*?)</poem>", lambda m: "\n" + "\n".join("@V@" + x.strip(SP + " ") for x in m.group(1).strip().split("\n") if x.strip(SP + " ")) + "\n", body, flags=re.S)
    out = []
    for block in re.split(r"\n\s*\n", body):
        cur, cur_kind = None, None

        def flush():
            if cur is not None:
                out.append((cur_kind, cur))

        for ln in block.split("\n"):
            ln = re.sub(r"<br\s*/?>\s*$", "", ln.rstrip())
            if not ln.strip():
                continue
            verse = False
            if ln.startswith("@V@"):
                verse, text = True, ln[3:]
            else:
                m = re.match(r"\{\{center\|(.*)\}\}$", ln.strip(), flags=re.S)
                if m:
                    verse, text = True, m.group(1)
                elif ln.startswith("::"):
                    verse, text = True, ln.lstrip(":")
                else:
                    lead = len(ln) - len(ln.lstrip(SP + " "))       # 数缩进（行首的零宽空格之前）
                    plain = re.sub(r"〈[^〉]*〉|<ref[^>]*>.*?</ref>|<[^>]*>", "", ln.replace(BOM, "")).strip(SP + " ")
                    verse, text = lead >= 3 and len(plain) <= 45, ln     # 缩进的长句是文书（如履历），不是诗
            text = text.replace(BOM, "").strip(SP + " ")
            if not text:
                continue
            if verse and cur_kind == "诗":
                # 单独成行的脂批并到上一行末尾，不另起一句
                solo = text.startswith("〈") and text.endswith("〉") and text.count("〈") == text.count("〉") and text.find("〉") == len(text) - 1 - (text.count("〉") - 1) * 0 and text[1:-1].find("〈") < 0 and text[1:-1].find("〉") < 0
                cur += text if solo else "/" + text
            else:
                flush()
                cur, cur_kind = text, "诗" if verse else "原"
        flush()
    return [(k, t) for k, t in out if t.strip()]


def toc_titles():
    """总目录页里每回的回目（页面自己的 header 偶尔只写“第五回”，缺回目时用它补）。"""
    w = json.loads((RAW / "_main.json").read_text(encoding="utf8"))["wikitext"]
    out = {}
    for m in re.finditer(r"\*\[\[/第([^|\]]+)回\|[^\]]*\]\]\u3000(.+)", w):
        out[m.group(1)] = re.sub(r"\s+", " ", m.group(2).replace(SP, " ")).strip()
    return out


def convert_page(key, data):
    w = data["wikitext"]
    hm = re.search(r"\{\{header(.*?)\n\}\}", w, flags=re.S)
    head = hm.group(1)
    sm = re.search(r"\|\s*section\s*=\s*(.*)", head)
    title = strip_markup(sm.group(1)).replace(SP, " ").strip() if sm else ""
    lead = re.findall(r"\{\{\s*~~?\s*\|((?:(?!\}\}).)*)\}\}", title)     # 回目里夹的批语，移到正文开头
    title = re.sub(r"\{\{[^{}]*\}\}", "", title)
    title = re.sub(r"\s+", " ", title.replace(SP, " ")).strip() if lead else title
    m = re.fullmatch(r"第([一二三四五六七八九十]+)回", title.strip())
    if m:
        name = TOC.get(m.group(1))
        assert name, (key, title)
        title = f"第{m.group(1)}回 {name}"
    if key == "qixu":
        title = "戚蓼生序"
    body = w[hm.end():]
    body = re.sub(r"==\s*注释\s*==.*", "", body, flags=re.S)
    body = re.split(r"\{\{[Ff]ooter", body)[0]
    body = re.sub(r"\[\[[Cc]ategory:[^\]]*\]\]", "", body)
    sections = []   # (小节标题或 None, [段落])
    if key == "067":
        parts = re.split(r"\n==([^=\n]+)==\n", body)
        for i in range(1, len(parts), 2):
            sections.append((parts[i].strip(), paragraphs(parts[i + 1])))
        # 去掉每个版本自带的回目标题行
        sections = [(n, [(k, p) for k, p in ps if not re.match(r"第\s*六\s*十\s*七\s*回", p)]) for n, ps in sections]
    else:
        ps = paragraphs(body)
        # 去掉与回目重复的标题行（{{center|第X回 …}}）与“戚蓼生序”标题
        ps = [(k, p) for k, p in ps if not re.match(r"^\s*第\s*[一二三四五六七八九十]+\s*回", strip_markup(p).replace(SP, " ")) and strip_markup(p) != "戚蓼生序"]
        ps = [("原", "〈" + x.strip() + "〉") for x in lead] + ps
        sections.append((None, ps))
    lines = []
    for n, (name, ps) in enumerate(sections):
        t = title if n == 0 else name
        lines.append("# " + cc.convert(t))
        for kind, p in ps:
            notes = []
            txt = strip_markup(clean_inline(p, notes))
            txt = cc.convert(txt)
            txt = txt.replace("【", "").replace("】", "")     # 批语外框；批语已用〈〉标成小字，站内【】会被当作曲牌样式
            assert not re.search(r"\{\{|\}\}|<|>|\[\[|\]\]", txt), (key, txt[:120])
            lines.append(kind + "：" + txt)
            for k, nt in enumerate(notes):
                lines.append("注原：" + CIRC[k] + "　" + cc.convert(nt))
    return "\n".join(lines) + "\n"


TOC = None


def main():
    global TOC
    TOC = toc_titles()
    for f in sorted(RAW.glob("*.json")):
        if f.name.startswith("_"):
            continue
        data = json.loads(f.read_text(encoding="utf8"))
        out = OUT / data["key"] / "01.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(convert_page(data["key"], data), encoding="utf8")
    print("ok", len(list(OUT.glob("*/01.txt"))))


if __name__ == "__main__":
    main()
