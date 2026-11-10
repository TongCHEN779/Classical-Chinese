#!/usr/bin/env python3
"""核验《长物志》标点稿：sources/changwuzhi/punct/<页>.json 必须与 chapters.json 同形，且去掉标点后与原文逐字相同。
  python3 tools/check_punct.py 页slug ...
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUNCT = "。，、；：？！“”‘’《》（）…—·　 "


def strip(t):
    return "".join(c for c in t if c not in PUNCT)


def main(slugs):
    chap = {c["slug"]: c for c in json.loads((ROOT / "sources/changwuzhi/chapters.json").read_text(encoding="utf8"))}
    bad = 0
    for sl in slugs:
        f = ROOT / "sources/changwuzhi/punct" / f"{sl}.json"
        if not f.exists():
            print(sl, "缺稿"); bad += 1; continue
        got = json.loads(f.read_text(encoding="utf8"))
        want = [s["paragraphs"] for s in chap[sl]["sections"]]
        if len(got) != len(want) or any(len(a) != len(b) for a, b in zip(got, want)):
            print(sl, "节数/段数与原文不同"); bad += 1; continue
        for i, (a, b) in enumerate(zip(got, want)):
            for k, (x, y) in enumerate(zip(a, b)):
                if strip(x) != strip(y):
                    print(sl, f"节{i}段{k} 与原文字不同：", x[:30], "|", y[:30]); bad += 1
                if not re.search(r"[。！？”」]$", x) and len(strip(x)) > 14:
                    print(sl, f"节{i}段{k} 长段未以句末标点结尾：", x[-12:]); bad += 1
    print("OK" if not bad else f"{bad} 处问题")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:]) else 0)
