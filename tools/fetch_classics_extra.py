#!/usr/bin/env python3
"""缓存“经典名篇”新增篇目的维基文库原文，格式同 sources/classic_list/wikisource/*.json。

  python3 tools/fetch_classics_extra.py [slug ...]
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch

OUT = ROOT / "sources/classic_list/wikisource"
PAGES = {"aijiangnan": "哀江南賦", "yugu": "與顧章書", "yusong": "與宋元思書", "maiyou": "賣油翁", "yuchen": "與陳伯之書"}
# 第三批（用户 2026-11 补充的 37 篇）；同名异作的页面取带作者括注的标题
PAGES.update({"shaonian": "少年中國說", "bingmei": "病梅館記", "huangshan": "遊黃山記", "taishan": "登泰山記", "zuozhongyi": "左忠毅公軼事",
              "yuzhongzaji": "獄中雜記", "jimei": "祭妹文", "qinshi": "秦士錄", "maigan": "賣柑者言", "shenlv": "深慮論",
              "yurang": "豫讓論", "xiangci": "象祠記", "zunjingge": "尊經閣記", "xianbi": "先妣事略 (歸有光)",
              "canglang-gui": "滄浪亭記 (歸有光)", "canglang-su": "滄浪亭記 (蘇舜欽)", "hanhua": "寒花葬誌", "zhuxi": "任光祿竹溪記",
              "xinling": "信陵君救趙論", "huqiu": "虎丘記", "manjing": "滿井遊記", "yuejianglou": "閱江樓記", "mozhu": "墨竹賦",
              "shangzhongyong": "傷仲永", "mengchang": "讀孟嘗君傳", "dasima": "答司馬諫議書", "changhen": "長恨歌",
              "changan": "長安古意", "xiaoyuan": "小園賦", "kushu": "枯樹賦", "daleilei": "登大雷岸與妹書", "lingguan": "五代史伶官傳序",
              "daolouyuan": "待漏院記", "pengdang": "朋黨論 (歐陽脩)", "qiusheng": "秋聲賦", "fengle": "豐樂亭記", "wucheng": "蕪城賦"})


def blocks_of(root):
    for x in root.select("table, .licenseContainer, style, meta, link, #headerContainer, ol.references, sup.reference, span.variant-tooltip"):
        x.decompose()
    for x in root.select("div.prose, div.poem"):
        x.unwrap()
    out = []
    for el in root.find_all(["p", "dl", "ul", "ol", "div", "h2", "h3", "h4"], recursive=False):
        tag = el.name
        if tag == "div" and "mw-heading" in (el.get("class") or []):
            h = el.find(re.compile("h[1-6]"))
            out.append({"type": h.name, "text": h.get_text(strip=True)})
        elif tag == "p":
            t = re.sub(r"\s+", " ", el.get_text("", strip=False)).replace("　", "").strip()
            if t:
                out.append({"type": "p", "text": t})
        elif tag in ("dl", "ul", "ol"):
            for li in el.find_all(["dd", "li"]):
                t = re.sub(r"\s+", " ", li.get_text("", strip=False)).replace("　", "").strip()
                if t:
                    out.append({"type": li.name, "text": t})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, title in PAGES.items():
        if len(sys.argv) > 1 and slug not in sys.argv[1:]:
            continue
        page = fetch(title)
        root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
        blocks = blocks_of(root)
        raw = "\n".join(b["text"] for b in blocks)
        data = {"title": title, "query": title, "url": "https://zh.wikisource.org/zh-hans/" + quote(title), "revision": str(page["revid"]),
                "fetched_at": datetime.now(timezone.utc).isoformat(), "blocks": blocks,
                "text_sha256": hashlib.sha256(raw.encode("utf8")).hexdigest()}
        (OUT / f"{slug}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf8")
        print(slug, title, page["revid"], len(blocks), sum(len(b["text"]) for b in blocks))


if __name__ == "__main__":
    main()
