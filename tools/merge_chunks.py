#!/usr/bin/env python3
"""把“标题·首句…”式的切块小节并回原标题一节（用现成的篇名作子目录），同步合并 annotations。
  python3 tools/merge_chunks.py yuejueshu chunqiufanlu wuyuechunqiu youyangzazu
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_texts import load_draft


def main():
    for book in sys.argv[1:]:
        cp = ROOT / "sources" / book / "chapters.json"
        chs = json.loads(cp.read_text(encoding="utf8"))
        adir = ROOT / "sources" / book / "annotations"
        for ch in chs:
            secs = ch["sections"]
            draft = load_draft(book, ch["slug"], len(secs))
            groups = []                       # [(新标题, [旧序号])]
            for i, s in enumerate(secs):
                t = s["title"]
                if "·" in t:
                    head = t.split("·", 1)[0]
                    if groups and groups[-1][2] == head:
                        groups[-1][1].append(i)
                        continue
                    groups.append([head, [i], head])
                else:
                    groups.append([t, [i], None])
            new_secs, items = [], []
            for head, idx, _ in groups:
                base = dict(secs[idx[0]])
                base["title"] = head
                base["paragraphs"] = [p for i in idx for p in secs[i]["paragraphs"]]
                new_secs.append(base)
                its = [draft[i] or {} for i in idx]
                guide = "".join(x.get("题解", "").strip() for x in its)
                paras = []
                for k, i in enumerate(idx):
                    n = len(secs[i]["paragraphs"])
                    ps = list(its[k].get("段落", []))
                    ps += [{}] * (n - len(ps))
                    paras += ps
                items.append({"题解": guide, "段落": paras})
            for f in adir.glob(f"{ch['slug']}__*.json"):
                f.unlink()
            ch["sections"] = new_secs
            (adir / f"{ch['slug']}__0.json").write_text(json.dumps({"start": 0, "items": items}, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        cp.write_text(json.dumps(chs, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print(book, sum(len(c["sections"]) for c in chs))


if __name__ == "__main__":
    main()
