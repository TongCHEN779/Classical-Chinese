#!/usr/bin/env python3
"""缓存维基文库《脂硯齋重評石頭記》的 82 个页面（戚序、凡例、第一回至第八十回）的 wikitext 到 sources/shitouji/raw/。

  python3 tools/fetch_shitouji.py
"""
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from catalog_zizhitongjian import API, get

RAW = ROOT / "sources/shitouji/raw"
CN = "零一二三四五六七八九"


def cn(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n - 10] if n > 10 else "")
    t, u = divmod(n, 10)
    return CN[t] + "十" + (CN[u] if u else "")


def fetch(title, retries=6):
    for attempt in range(retries):
        try:
            time.sleep(1.5)
            return json.loads(get(API, {"action": "parse", "page": title, "prop": "wikitext|revid", "format": "json", "formatversion": 2}))["parse"]
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(4 * 2 ** attempt)


def main():
    pages = [("qixu", "戚序"), ("fanli", "凡例")] + [(f"{n:03d}", f"第{cn(n)}回") for n in range(1, 81)]
    base = "脂硯齋重評石頭記"
    meta = {}
    for key, name in pages:
        f = RAW / f"{key}.json"
        if f.exists():
            continue
        d = fetch(f"{base}/{name}")
        f.write_text(json.dumps({"key": key, "page": f"{base}/{name}", "revid": d["revid"], "wikitext": d["wikitext"]}, ensure_ascii=False), encoding="utf8")
        print(key, name, len(d["wikitext"]), flush=True)
    d = fetch(base)
    (RAW / "_main.json").write_text(json.dumps({"revid": d["revid"], "wikitext": d["wikitext"]}, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main()
