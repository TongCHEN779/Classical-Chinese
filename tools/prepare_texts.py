"""由 sources/<book>/chapters.json（维基文库原文）与 annotations/<页>__<起始节>.json 的自撰题解、白话、注释
生成 src/<book>/<页>/01.txt。适用于 tools/fetch_texts.py 抓取的各书。

annotations/<页>__<起始节>.json：{"start": 起始节序号, "items": [{"题解": "...", "段落": [{"译": ["每句白话"], "注": ["词语：解释"]}, ...]}, ...]}
items 与该页从 start 起的各节一一对应。

  python3 tools/prepare_texts.py [book ...]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import sent_units, split_sents

TEXT_BOOKS = ["shipin", "weilu", "caigentan", "fusheng", "zengguang", "yanshi", "sunzi", "sunbin",
              "fansheng", "yinwenzi", "shenbuhai", "shendao",
              "huafanglu", "taoan", "dijing", "ducheng", "mengliang", "xuxiake",
              "shanhaijing", "jinbenzhushu", "mutianzi", "yandanzi",
              "diwangshiji", "yuejueshu", "chunqiufanlu", "wuyuechunqiu", "youyangzazu", "wenxindiaolong", "guanzi", "liexianzhuan",
              "zhenguanzhengyao", "tiangongkaiwu", "dutongjianlun", "rizhilu",
              "xingmingguizhi", "canglangshihua", "baiyuzhaicihua", "qiminyaoshu", "wulinjiushi", "wenshitongyi", "kunxuejiwen",
              "wulixiaoshi", "changwuzhi", "yuanye", "ershierzhaji", "hanshu", "houhanshu", "sanguozhi", "jinshu", "shiliuguochunqiu", "nanshi"]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def load_draft(book, page, n):
    draft = [None] * n
    for f in sorted((ROOT / "sources" / book / "annotations").glob(f"{page}__*.json")):
        if "__tijie" in f.name:
            continue
        d = read(f)
        for k, item in enumerate(d["items"]):
            assert d["start"] + k < n, (f.name, k)
            draft[d["start"] + k] = item
    # 题解可单独成文件 <页>__tijie_<起始节>.json：{"start": 起始节, "题解": [每节一条]}，只补空的题解（徐霞客游记按日分节后用）
    for tj in sorted((ROOT / "sources" / book / "annotations").glob(f"{page}__tijie*.json")):
        t = read(tj)
        for k, g in enumerate(t["题解"]):
            i = t.get("start", 0) + k
            assert i < n, (tj.name, k)
            if draft[i] is not None and not draft[i].get("题解", "").strip():
                draft[i]["题解"] = g
    return draft


def prepare(books=None):
    report = []
    for book in books or TEXT_BOOKS:
        path = ROOT / "sources" / book / "chapters.json"
        if not path.exists():
            continue
        for ch in read(path):
            slug = ch["slug"]
            draft = load_draft(book, slug, len(ch["sections"]))
            lines, total, done = [], 0, 0
            for i, sec in enumerate(ch["sections"]):
                item = draft[i] or {}
                lines.append(f"# {sec['title']}")
                if guide := item.get("题解", "").strip():
                    lines.append(f"题解：{guide}")
                paragraphs = item.get("段落", [])
                assert len(paragraphs) <= len(sec["paragraphs"]), (book, slug, i)
                for j, original in enumerate(sec["paragraphs"]):
                    n = len(sent_units(original))
                    total += n
                    data = (paragraphs[j] or {}) if j < len(paragraphs) else {}
                    gloss = [t.strip() for t in data.get("译", [])]
                    if gloss:
                        assert len(gloss) == n and all(t and not any(c in t for c in "¦\r\n|") for t in gloss), (book, slug, i, j, n, len(gloss))
                        lines.append(f"原：{original} || {'¦'.join(gloss)}")
                        done += n
                    else:
                        lines.append(f"原：{original}")
                    for x in data.get("注", []):
                        assert "：" in x and x.split("：", 1)[0].strip(), (book, slug, i, j, x)
                        assert x.split("：", 1)[0].strip() in original, (book, slug, i, j, "注的词语不在原文里", x[:20])
                        lines.append(f"注：{x.strip()}")
            target = ROOT / "src" / book / slug / "01.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(lines) + "\n", encoding="utf8")
            report.append((book, slug, done, total))
    return report


if __name__ == "__main__":
    rep = prepare(sys.argv[1:] or None)
    last = None
    for book, slug, done, total in rep:
        print(book, slug, done, "/", total)
    print("合计", sum(r[2] for r in rep), "/", sum(r[3] for r in rep))
