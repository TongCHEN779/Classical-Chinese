#!/usr/bin/env python3
"""只录原文的大书抓取进度表。  python3 tools/fetch_progress.py [日志路径]   （每 5 秒刷新，Ctrl-C 退出）"""
import glob
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("/private/tmp/claude-*/**/scratchpad/fo_seq.log", recursive=True))[-1]
# (slug, 书名, 预计页数)
BOOKS = [("shuijingzhu", "水经注", 41), ("taipingguangji", "太平广记", 500), ("houhanshu", "后汉书", 131), ("hanshu", "汉书", 110),
         ("sanguozhi", "三国志", 67), ("jinshu", "晋书", 130), ("nanshi", "南史", 80), ("beishi", "北史", 100), ("suishu", "隋书", 86),
         ("songshu", "宋书", 100), ("nanqishu", "南齐书", 62), ("liangshu", "梁书", 56), ("chenshu", "陈书", 37), ("weishu", "魏书", 131),
         ("beiqishu", "北齐书", 50), ("zhoushu", "周书", 50), ("jiutangshu", "旧唐书", 215), ("xintangshu", "新唐书", 249),
         ("jiuwudaishi", "旧五代史", 151), ("xinwudaishi", "新五代史", 74), ("liaoshi", "辽史", 117), ("jinshi", "金史", 136),
         ("yuanshi", "元史", 211), ("mingshi", "明史", 332), ("songshi", "宋史", 497), ("tongdian", "通典", 200),
         ("wenxiantongkao", "文献通考", 163), ("ershierzhaji", "廿二史劄记", 38)]


def pad(text, width):
    """按显示宽度补空格（汉字占两格），让进度条起点对齐。"""
    w = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    return text + " " * (width - w)


def snapshot():
    log = Path(LOG).read_text(encoding="utf8", errors="ignore") if Path(LOG).exists() else ""
    rows, tot, tot_all = [], 0, 0
    for slug, name, n in BOOKS:
        done = set(re.findall(rf"^{slug} (\S+) .* \| ", log, re.M))
        c = ROOT / "sources" / slug / "chapters.json"
        if c.exists():
            try:
                done |= {x["slug"] for x in json.loads(c.read_text(encoding="utf8"))}
            except Exception:
                pass
        skips = len(re.findall(rf"^SKIP {slug} ", log, re.M))
        rows.append((name, len(done), n, skips))
        tot += len(done)
        tot_all += n
    return rows, tot, tot_all, "ALLDONE" in log


def main():
    while True:
        rows, tot, tot_all, fin = snapshot()
        out = ["\033[2J\033[H" + f"抓取进度  {time.strftime('%H:%M:%S')}  合计 {tot}/{tot_all}  ({tot * 100 // tot_all}%)" + ("  全部结束" if fin else "")]
        for name, d, n, sk in rows:
            bar = "█" * min(d * 20 // n, 20) + "░" * (20 - min(d * 20 // n, 20))
            out.append(f"{pad(name, 12)}{bar} {d:>4}/{n:<4}" + (f"  跳过{sk}" if sk else "") + ("  ✓" if d >= n else ""))
        print("\n".join(out), flush=True)
        if fin or "--once" in sys.argv:
            break
        time.sleep(5)


if __name__ == "__main__":
    main()
