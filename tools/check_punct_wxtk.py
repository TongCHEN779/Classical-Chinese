#!/usr/bin/env python3
"""核验四库本《文献通考》缺卷的标点稿：sources/wenxiantongkao/punct/<卷>.json 必须是字符串数组，
与 sk_pages.json 里该卷的段落一一对应，去掉标点后与原文逐字相同（〈〉要留在原位）。
  python3 tools/check_punct_wxtk.py 卷号 ...
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUNCT = "。，、；：？！“”‘’《》（）…—·　 "
END = "。？！”’"


def strip(t):
    return "".join(c for c in t if c not in PUNCT)


def main(ks):
    pages = json.loads((ROOT / "sources/wenxiantongkao/sk_pages.json").read_text(encoding="utf8"))
    bad = 0
    for k in ks:
        f = ROOT / "sources/wenxiantongkao/punct" / f"{k}.json"
        if not f.exists():
            print(k, "缺稿"); bad += 1; continue
        got = json.loads(f.read_text(encoding="utf8"))
        want = pages[str(k)]["paragraphs"]
        if not isinstance(got, list) or len(got) != len(want):
            print(k, f"段数不同：稿 {len(got) if isinstance(got, list) else '非数组'} / 原文 {len(want)}"); bad += 1; continue
        for i, (x, y) in enumerate(zip(got, want)):
            if strip(x) != strip(y):
                print(k, f"段{i} 与原文字不同：", x[:30], "|", y[:30]); bad += 1
                continue
            # 原书按行分段，行可能断在句中或小注中间：段尾不强求句末标点，句子没写完就不要硬补
            if len(strip(x)) <= 30 and not x.endswith(tuple(END + "〉")) and any(c in x for c in "。？！；"):
                print(k, f"段{i} 短行（小标题）却带了标点：", x[:30]); bad += 1
    print("OK" if not bad else f"{bad} 处问题")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:]) else 0)
