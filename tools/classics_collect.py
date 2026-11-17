#!/usr/bin/env python3
"""把“经典名篇”里同一作者的几篇合成一个“选文”条目（做法同 liuguo：collected_works，每节各自登记来源）。

  python3 tools/classics_collect.py        合并 COLLECTIONS 里尚未合并的各条

对每个成员篇：
  - 已登记的独立条目：取其来源与 provenance，src 稿并入合集目录（标题改成“篇名｜［朝代］作者”），旧条目与旧 src 目录删去，旧网址设重定向；
  - 尚未登记的新篇（classics_batch3.py 的 SPECS，check 必须通过）：由 make_entry 生成来源与 provenance；
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import classics_batch3 as b3
import build

CL = ROOT / "sources/classic_list"
SRC = ROOT / "src/classic_list"

COLLECTIONS = [
    dict(slug="zhangdai", title="张岱选文", author="［明］张岱",
         intro="合收张岱小品与序跋五篇：《湖心亭看雪》《西湖七月半》《〈西湖梦寻〉自序》《明圣二湖》《自为墓志铭》。",
         members=["huxinting", "qiyueban", "xihumengxunxu", "mingshengerhu", "zibumuzhiming"]),
    dict(slug="zhugeliang", title="诸葛亮选文", author="［三国蜀］诸葛亮",
         intro="合收诸葛亮《出师表》（前）、《后出师表》和《诫子书》三篇。",
         members=["chushi", "houchushi", "jiezishu"]),
    dict(slug="tangxianzu", title="汤显祖选文", author="［明］汤显祖",
         intro="合收汤显祖论戏曲与性情的文章与尺牍五篇：《牡丹亭题词》《答岳石帆》《与岳石梁》《答屠纬真》《宜黄县戏神清源师庙记》。",
         members=["mudantingtici", "dayueshifan", "yueshiliang", "datuweizhen", "qingyuanshi"]),
    dict(slug="lizhi", title="李贽选文", author="［明］李贽",
         intro="合收李贽《杂说》《童心说》《高洁说》三篇，谈文章的“化工”、人的“童心”与自己的好高好洁。",
         members=["lizhizashuo", "tongxinshuo", "gaojieshuo"]),
]


def section_of(member, entries_by_slug):
    """返回 (节标题, 作者, 稿子文本, 来源, provenance)。"""
    entry = entries_by_slug.get(member)
    if entry is None:
        spec = b3.BY[member]
        assert b3.check(member), member
        entry = b3.make_entry(spec)
    text = (SRC / member / "001.txt").read_text(encoding="utf8")
    title = f"{entry['title']}｜{entry['author']}"
    text = re.sub(r"\A# .*\n", f"# {title}\n", text)
    original = "".join(l[2:].split("||")[0].strip() for l in text.split("\n") if l.startswith("原："))
    prov = dict(entry["provenance"])
    prov["original_sha256"] = hashlib.sha256(original.replace("/", "").encode()).hexdigest()
    return title, entry["author"], text, dict(entry["source"]), prov, original


def main():
    path = CL / "entries.json"
    entries = json.loads(path.read_text(encoding="utf8"))
    have = {e["slug"] for e in entries}
    for col in COLLECTIONS:
        if col["slug"] in have:
            print("已有", col["slug"]); continue
        by = {e["slug"]: e for e in entries}
        secs, redirects, originals = [], {}, []
        outdir = SRC / col["slug"]
        outdir.mkdir(parents=True, exist_ok=True)
        for i, member in enumerate(col["members"], 1):
            title, author, text, source, prov, original = section_of(member, by)
            (outdir / f"{i:03d}.txt").write_text(text.rstrip("\n") + "\n", encoding="utf8")
            secs.append({"title": title, "author": author, "source": source, "provenance": prov})
            originals.append(original)
            if member in by:      # 原来单独成页的，旧网址跳到合集里对应节
                redirects[member] = f"{col['slug']}.html#e{i}"
        # 原文摘要：与 check_classics 一致，取各节原文拼接（“/”换行记号不计）
        whole = "".join(o.replace("/", "") for o in originals)
        entry = {"title": col["title"], "author": col["author"], "intro": col["intro"], "slug": col["slug"],
                 "provenance": {"kind": "collected_works", "original_sha256": hashlib.sha256(whole.encode()).hexdigest()},
                 "sections": secs, "redirects": redirects}
        gone = set(redirects)
        entries = [e for e in entries if e["slug"] not in gone]
        entries.append(entry)
        for slug in gone | set(col["members"]):
            d = SRC / slug
            if d.exists():
                shutil.rmtree(d)
        print("合并", col["slug"], [s["title"] for s in secs])
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
