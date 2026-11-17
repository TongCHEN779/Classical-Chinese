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
import opencc

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
              "daolouyuan": "待漏院記", "pengdang": "朋黨論 (歐陽脩)", "qiusheng": "秋聲賦", "fengle": "豐樂亭記", "wucheng": "蕪城賦", "changhenzhuan": "長恨歌傳"})

# 第四批（2026-11，据新语丝 classics/prose 筛出站内没有的篇目；原文一律取维基文库）
PAGES.update({"xihuzaji": "西湖雜記 (袁宏道)", "xihumengxunxu": "西湖夢尋/自序", "zibumuzhiming": "自為墓誌銘 (張岱)", "mingshengerhu": "西湖夢尋/總記",
              "shangjieting": "尚節亭記", "jiaotiaolongchang": "教條示龍場諸生", "chengtiansi": "記承天寺夜遊", "xunjianshikang": "訓儉示康",
              "bailudong": "白鹿洞書院學規", "zhengqige": "正氣歌", "songqinzhong": "送秦中諸人引", "shangzhizhai": "尚志齋說",
              "yugong": "列子/湯問篇", "jiezishu": "誡子書", "qianziwen": "千字文", "yangzhoushiri": "揚州十日記", "huixinji": "敘陳正甫會心集",
              "tongxinshuo": "焚書/卷3", "lizhizashuo": "焚書/卷3", "gaojieshuo": "李溫陵集"})
# 第五批（2026-11）：张岱、诸葛亮、汤显祖选文所需篇目，以及《金人铭》《柳敬亭传》
PAGES.update({"qiyueban": "西湖七月半", "houchushi": "後出師表", "mudantingtici": "牡丹亭題詞", "dayueshifan": "答岳石帆", "yueshiliang": "與岳石梁",
              "datuweizhen": "答屠緯真", "qingyuanshi": "宜黃縣戲神清源師廟記", "jinrenming": "金人銘", "liujingtingzhuan": "柳敬亭傳"})
# 整页很大、只要其中一节的：slug -> (起始块的正则, 结束块的正则或 None=到下一个同类标题/页尾)；缓存里只留这一节的块
TRIM = {"tongxinshuo": (r"^童心说$", r"^心经提纲$"), "lizhizashuo": (r"^杂说$", r"^童心说$"), "gaojieshuo": (r"^○高洁说", r"^○")}


def trim(blocks, slug):
    if slug not in TRIM:
        return blocks
    s, e = TRIM[slug]
    i = next(k for k, b in enumerate(blocks) if re.search(s, b["text"]))
    j = next((k for k in range(i + 1, len(blocks)) if re.search(e, blocks[k]["text"])), len(blocks))
    return blocks[i + 1:j] if blocks[i]["type"].startswith("h") or blocks[i]["text"].startswith("○") and len(blocks[i]["text"]) <= 6 else blocks[i:j]


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
    if not out:
        box = root.select_one("div.prp-pages-output, div.Kaiti, div.prose")
        if box:
            for x in box.select("span.pagenum, style, span.ws-noexport"):
                x.decompose()
            for el in box.find_all(["p", "h2", "h3"]):
                t = re.sub(r"\s+", " ", el.get_text("", strip=False)).replace("\u200b", "").replace("　", "").strip()
                if t:
                    out.append({"type": "p" if el.name == "p" else el.name, "text": t})
    if not out:      # 汤显祖尺牍等整段放在 <pre> 里
        for el in root.find_all("pre"):
            t = re.sub(r"\s+", " ", el.get_text("", strip=False)).replace("　", "").strip()
            if t:      # <pre> 里的字维基文库不做简繁转换，这里用 opencc t2s 转成与其他页一致的简体
                out.append({"type": "p", "text": opencc.OpenCC("t2s").convert(t)})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, title in PAGES.items():
        if len(sys.argv) > 1 and slug not in sys.argv[1:]:
            continue
        page = fetch(title)
        root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
        blocks = trim(blocks_of(root), slug)
        raw = "\n".join(b["text"] for b in blocks)
        data = {"title": title, "query": title, "url": "https://zh.wikisource.org/zh-hans/" + quote(title), "revision": str(page["revid"]),
                "fetched_at": datetime.now(timezone.utc).isoformat(), "blocks": blocks,
                "text_sha256": hashlib.sha256(raw.encode("utf8")).hexdigest()}
        (OUT / f"{slug}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf8")
        print(slug, title, page["revid"], len(blocks), sum(len(b["text"]) for b in blocks))


if __name__ == "__main__":
    main()
