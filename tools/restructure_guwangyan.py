#!/usr/bin/env python3
"""《姑妄言》各回整理成“一回一页一节”：页标题 = 回目，去掉“正文”小节和“《姑妄言》第N卷评”标题行，
卷评（钝翁曰……）与回文合并为同一节，卷评段数记在 sources/guwangyan/ping.json（页面上以小字灰体显示）。
已写好的注释文件（annotations）一并并入：卷评节与回文节合成一项。一次性迁移脚本，可重复运行（已合并的页自动跳过）。

  python3 tools/restructure_guwangyan.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "sources/guwangyan"


def main():
    chapters = json.loads((D / "chapters.json").read_text(encoding="utf8"))
    ping = json.loads((D / "ping.json").read_text(encoding="utf8")) if (D / "ping.json").exists() else {}
    titles = {}
    for ch in chapters:
        secs = ch["sections"]
        if len(secs) != 2 or secs[0]["title"] != "正文" or not re.match(r"^《姑妄言》第.+卷评$", secs[0]["paragraphs"][0]):
            continue
        s0, s1 = secs
        paras1 = list(s1["paragraphs"])
        dropped_title_line = False
        if re.match(r"^第.+回", s1["title"]):
            title = s1["title"]
        else:                                           # 回目在回文首段（如第二十二回）
            m = re.match(r"^(第.+回 .+)$", paras1[0])
            assert m, (ch["slug"], paras1[0][:30])
            title = paras1.pop(0)
            dropped_title_line = True
        pings = s0["paragraphs"][1:]
        n0 = len(s0["paragraphs"])
        # 注释迁移
        ann0 = D / "annotations" / f"{ch['slug']}__0.json"
        ann1 = D / "annotations" / f"{ch['slug']}__1.json"
        if ann0.exists():
            a0 = json.loads(ann0.read_text(encoding="utf8"))
            a1 = json.loads(ann1.read_text(encoding="utf8")) if ann1.exists() else None
            i0 = a0["items"][0]
            if i0["段落"][0].get("注"):
                print("丢弃标题行的注", ch["slug"], i0["段落"][0]["注"])
            seg0 = i0["段落"][1:]
            seg0 += [{"译": [], "注": []}] * (len(pings) - len(seg0))
            if a1:
                i1 = a1["items"][0]
                seg1 = i1["段落"]
                if dropped_title_line:
                    seg1 = seg1[1:]
                guide = i1.get("题解", "")
                seg = seg0 + seg1
            else:
                guide, seg = i0.get("题解", ""), seg0
            ann0.write_text(json.dumps({"start": 0, "items": [{"题解": guide, "段落": seg}]}, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
            if ann1.exists():
                ann1.unlink()
        ch["sections"] = [{"title": title, "level": s1["level"], "path": s1.get("path", []), "author": s1.get("author", ""), "paragraphs": pings + paras1}]
        ping[ch["slug"]] = len(pings)
        titles[ch["slug"]] = title
        ch["title"] = title
    (D / "chapters.json").write_text(json.dumps(chapters, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (D / "ping.json").write_text(json.dumps(ping, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    pages = json.loads((D / "pages.json").read_text(encoding="utf8"))
    for p in pages:
        if p[0] in titles:
            p[1] = titles[p[0]]
    (D / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("合并", len(titles), "回")


if __name__ == "__main__":
    main()
