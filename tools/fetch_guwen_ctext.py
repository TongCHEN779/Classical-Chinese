#!/usr/bin/env python3
"""《古文辞类纂》在维基文库尚缺的篇目（目录里的红链），改取中国哲学书电子化计划（ctext，维基版 res=625979，字符识别本、未校对）：
写入 sources/guwenciliezuan/ctext_fill.json，键为“卷名|目录原文”，值为 {paras, url}；tools/fetch_guwen.py 据此补入。

  python3 tools/fetch_guwen_ctext.py
ctext 对高频抓取会出验证码，间隔 7 秒（fetch_ctext_books.get），只取含缺篇的各卷，繁体转简体用 opencc t2s，不校改文字。
"""
import difflib
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fetch_ctext_books as f
import fetch_guwen as g

RES = 625979
OUT = ROOT / "sources/guwenciliezuan/ctext_fill.json"
CN = "零一二三四五六七八九十"


def key(s):
    return re.sub(r"[\s　（）()、，。]", "", f.T2S.convert(s))


def main():
    cache = ROOT / "sources/_guwen_cache"
    cache.mkdir(parents=True, exist_ok=True)
    info = json.loads((ROOT / "sources/guwenciliezuan/entries.json").read_text(encoding="utf8"))      # 先跑一遍 fetch_guwen.py，missing 即维基文库缺（红链或页面无正文）的篇目
    need = {}
    for m in info["missing"]:
        need.setdefault(m["vol"].split()[0], (m["vol"], []))[1].append({"rest": m["entry"]})
    print("缺篇所在卷", len(need), "缺", sum(len(v[1]) for v in need.values()), flush=True)
    h = f.get(f"https://ctext.org/wiki.pl?if=gb&res={RES}")
    s = BeautifulSoup(h, "html.parser")
    chap = {}
    for a in s.select("a[href*='chapter=']"):
        m = re.search(r"chapter=(\d+)(?:#|$)", a["href"])
        t = a.get_text(" ", strip=True)
        mv = re.match(r"^卷([一二三四五六七八九十]+) Volume", t)
        if m and mv and "#" not in a["href"]:
            chap["卷" + mv.group(1)] = m.group(1)
    fill = json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {}
    miss = []
    for vkey, (vt, red) in need.items():
        if vkey not in chap:
            miss += [(vt, e["rest"], "ctext 无此卷") for e in red]
            continue
        if all(f"{vt}|{e['rest']}" in fill for e in red):
            continue
        url = f"https://ctext.org/wiki.pl?if=gb&chapter={chap[vkey]}"
        hh = f.get(url)
        essays, cur = {}, None
        for k, t in f.rows(hh):
            if k == "H":
                title = re.sub(r"\s+[A-Za-z].*$", "", t.strip("《》 ")).strip()
                cur = key(title)
                essays[cur] = []
            elif cur is not None:
                essays[cur].append(f.T2S.convert(t))
        for e in red:
            k0 = key(e["rest"])
            hit = essays.get(k0)
            if hit is None:       # ctext 标题常省作者前缀、异体字不同：按篇名在各标题里取最相近者（须 ≥0.75）
                t = key(e["rest"].split(None, 1)[-1])
                used = {fill[x]["head"] for x in fill if x.startswith(vt + "|") and "head" in fill[x]}
                best, bh = 0, None
                for kk in essays:
                    if kk in used:
                        continue
                    sc = max(difflib.SequenceMatcher(None, t, kk[i:i + len(t) + 2]).ratio() for i in range(max(1, len(kk) - len(t) + 3)))
                    if sc > best:
                        best, bh = sc, kk
                if best >= 0.75:
                    hit, k0 = essays[bh], bh
                    print("  近似", e["rest"], "→", bh, round(best, 2), flush=True)
            if hit:
                fill[f"{vt}|{e['rest']}"] = {"paras": hit, "url": url, "head": k0}
            else:
                miss.append((vt, e["rest"], "卷内未找到"))
        print(vt, len(red), "补", sum(1 for e in red if f"{vt}|{e['rest']}" in fill), flush=True)
        OUT.write_text(json.dumps(fill, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    OUT.write_text(json.dumps(fill, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("补入", len(fill), "未补", len(miss))
    for m in miss:
        print("  缺", m)


if __name__ == "__main__":
    main()
