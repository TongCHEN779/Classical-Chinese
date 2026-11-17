#!/usr/bin/env python3
"""把“经典名篇”里同一作者的几篇合成一个“选文”条目（做法同 liuguo：collected_works，每节各自登记来源）。

  python3 tools/classics_collect.py              合并 COLLECTIONS 里尚未合并的各条（新篇目尚未单独登记时，先由 classics_batch3.make_entry 生成来源）
  python3 tools/classics_collect.py --by-author  把所有还有 2 篇以上的作者各合成“某某选文”（已是合集的不动）

对每个成员篇：
  - 单节的独立条目：取其来源与 provenance，src 稿并入合集目录（标题改成“篇名｜［朝代］作者”）；
  - 已分节的作品（永州八记、西湖杂记、教条示龙场诸生）：各节平铺进合集，节名写成“作品名·节名｜作者”；
  - 旧条目与旧 src 目录删去，旧网址设重定向到合集里对应的节（原有的重定向一并改指新位置）。
合并后各节与全篇的原文摘要，一律用 build.parse_poems 重新解析稿子计算。
"""
import hashlib
import json
import re
import shutil
import sys
from collections import OrderedDict
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
# 按作者归类时用的合集网址名
AUTHOR_SLUG = {"欧阳修": "ouyangxiu", "归有光": "guiyouguang", "王守仁": "wangshouren", "袁宏道": "yuanhongdao", "宋濂": "songlian",
               "庾信": "yuxin", "王安石": "wanganshi", "范仲淹": "fanzhongyan", "江淹": "jiangyan", "苏轼": "sushi", "柳宗元": "liuzongyuan",
               "白居易": "baijuyi", "吴均": "wujun", "方苞": "fangbao", "刘基": "liuji", "方孝孺": "fangxiaoru", "唐顺之": "tangshunzhi",
               "鲍照": "baozhao", "陶望龄": "taowangling"}


def name_of(author):
    return re.sub(r"^［[^］]*］", "", author)


def orig_of(text):
    return "".join(l[2:].split("||")[0].strip() for l in text.split("\n") if l.startswith("原："))


def sha(s):
    return hashlib.sha256(s.replace("/", "").encode()).hexdigest()


def sections_of_member(member, entries_by_slug, author):
    """返回 [(节标题, 稿子文本, 来源, provenance)]（节数 = 该成员的节数）。author 为合集统一采用的作者写法。"""
    entry = entries_by_slug.get(member)
    if entry is None:
        spec = b3.BY[member]
        assert b3.check(member), member
        entry = b3.make_entry(spec)
    srcdir = SRC / member
    if "sections" not in entry or entry["provenance"]["kind"] == "collected_works":
        text = (srcdir / "001.txt").read_text(encoding="utf8")
        title = f"{entry['title']}｜{author}"
        text = re.sub(r"\A# .*\n", f"# {title}\n", text)
        prov = dict(entry["provenance"]); prov["original_sha256"] = sha(orig_of(text))
        return [(title, text, dict(entry["source"]), prov)]
    # 已分节的作品：把各文件拼起来，再按“# ”标题切成各节
    whole = "".join((srcdir / f.name).read_text(encoding="utf8").rstrip("\n") + "\n" for f in sorted(srcdir.glob("*.txt")))
    parts = [p for p in re.split(r"(?m)^(?=# )", whole) if p.strip()]
    assert len(parts) == len(entry["sections"]), (member, len(parts), len(entry["sections"]))
    out, kind = [], entry["provenance"]["kind"]
    for i, (part, rec) in enumerate(zip(parts, entry["sections"])):
        title = f"{entry['title']}·{rec['title']}｜{author}"
        text = re.sub(r"\A# .*\n", f"# {title}\n", part)
        if kind == "grouped_witness":
            prov = dict(rec["provenance"])
        else:      # sectioned_cache：每节对应缓存里的一组块
            prov = {"kind": "cached_primary_text", "cache": entry["provenance"]["cache"], "selected_blocks": entry["provenance"]["section_blocks"][i]}
        prov["original_sha256"] = sha(orig_of(text))
        source = dict(rec["source"])
        if "after" not in source and entry.get("source", {}).get("after"):
            source["after"] = entry["source"]["after"]
        out.append((title, text, source, prov))
    return out


def collect(col, entries):
    by = {e["slug"]: e for e in entries}
    outdir = SRC / col["slug"]
    outdir.mkdir(parents=True, exist_ok=True)
    secs, redirects, n = [], {}, 0
    for member in col["members"]:
        parts = sections_of_member(member, by, col["author"])
        start = n + 1
        for title, text, source, prov in parts:
            n += 1
            (outdir / f"{n:03d}.txt").write_text(text.rstrip("\n") + "\n", encoding="utf8")
            secs.append({"title": title, "author": col["author"], "slug": member, "source": source, "provenance": prov})
        if member in by:      # 原来单独成页的：旧网址跳到合集里这一篇的第一节；原有的重定向一并指向新位置
            redirects[member] = f"{col['slug']}.html#e{start}"
            for old, target in by[member].get("redirects", {}).items():
                k = int(target.split("#e")[1]) if "#e" in target else 1
                redirects[old] = f"{col['slug']}.html#e{start + k - 1}"
    # 各节与全篇的原文摘要：用 build.parse_poems 重新解析稿子计算
    parsed = build.parse_poems(sorted(outdir.glob("*.txt")))
    assert len(parsed) == len(secs), (col["slug"], len(parsed), len(secs))
    whole = ""
    for s, rec in zip(parsed, secs):
        text = "".join(c["o"].replace("/", "") for c in s["chunks"])
        whole += text
        rec["provenance"]["original_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    return {"title": col["title"], "author": col["author"], "intro": col["intro"], "slug": col["slug"],
            "provenance": {"kind": "collected_works", "original_sha256": hashlib.sha256(whole.encode()).hexdigest()},
            "sections": secs, "redirects": redirects}


def replace_members(entries, col, entry):
    """合集条目放在第一个成员原来的位置（成员不在列表里的新篇目则放到末尾），删去各成员条目与旧稿目录。"""
    members = set(col["members"])
    out, placed = [], False
    for e in entries:
        if e["slug"] in members:
            if not placed:
                out.append(entry); placed = True
            continue
        out.append(e)
    if not placed:
        out.append(entry)
    for slug in members:
        d = SRC / slug
        if d.exists():
            shutil.rmtree(d)
    return out


def author_collections(entries):
    groups = OrderedDict()
    for e in entries:
        if e["provenance"]["kind"] == "collected_works":
            continue
        groups.setdefault(name_of(e["author"]), []).append(e)
    cols = []
    for name, es in groups.items():
        if len(es) < 2:
            continue
        slug = AUTHOR_SLUG[name]
        author = max({e["author"] for e in es}, key=len)      # 朝代写法有“宋/北宋”之分时取较具体的
        works = "".join(f"《{e['title']}》" for e in es)
        cols.append(dict(slug=slug, title=f"{name}选文", author=author, intro=f"合收{name}{len(es)}篇：{works}。",
                         members=[e["slug"] for e in es]))
    return cols


def main():
    path = CL / "entries.json"
    entries = json.loads(path.read_text(encoding="utf8"))
    cols = author_collections(entries) if "--by-author" in sys.argv else COLLECTIONS
    for col in cols:
        if col["slug"] in {e["slug"] for e in entries}:
            print("已有", col["slug"]); continue
        entry = collect(col, entries)
        entries = replace_members(entries, col, entry)
        print("合并", col["slug"], len(entry["sections"]), "节")
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
