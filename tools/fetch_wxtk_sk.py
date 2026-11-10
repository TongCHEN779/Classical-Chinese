#!/usr/bin/env python3
"""用维基文库“文獻通考 (四庫全書本)”补抓“文獻通考”里缺的卷，只存原文行，写入 sources/wenxiantongkao/sk_raw.json
（{卷号: [行...]}，四库本无标点，〈…〉是双行小注）。已抓的卷跳过；低频请求，避免被限流。
  python3 tools/fetch_wxtk_sk.py
"""
import json
import re
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_orig import page_of, cn2int

OUT = ROOT / "sources/wenxiantongkao/sk_raw.json"


def missing():
    have = set()
    for c in json.loads((ROOT / "sources/wenxiantongkao/chapters.json").read_text(encoding="utf8")):
        m = re.match(r"卷([一二三四五六七八九十百零〇]+)", c["title"])
        if m:
            have.add(cn2int(m.group(1)))
    return [n for n in range(1, 349) if n not in have]


def lines_of(soup):
    root = soup.select_one(".mw-parser-output")
    for x in root.select("table, .licenseContainer, style, .ws-header, #headerContainer, .noprint, sup.reference"):
        x.decompose()
    box = root.select_one("div.text") or root
    out = []
    for p in box.select("p"):
        for br in p.find_all("br"):
            br.replace_with("\n")
        for ln in p.get_text("").split("\n"):
            ln = re.sub(r"[ \t　]*$", "", ln.lstrip(" \t　"))
            ln = ln.replace("​", "")
            if ln.strip():
                out.append(ln.strip())
    return out


def main():
    data = json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {}
    for n in missing():
        if str(n) in data:
            continue
        try:
            wiki, p, soup, frag = page_of(f"文獻通考 (四庫全書本)/卷{n:03d}")
            data[str(n)] = lines_of(soup)
            print(n, len(data[str(n)]), sum(len(x) for x in data[str(n)]), flush=True)
        except Exception as e:
            print("FAIL", n, type(e).__name__, flush=True)
        OUT.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf8")
        time.sleep(3)


if __name__ == "__main__":
    main()
