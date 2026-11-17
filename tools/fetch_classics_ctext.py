#!/usr/bin/env python3
"""缓存“经典名篇”取自中国哲学书电子化计划（ctext）的篇目，格式同 sources/classic_list/wikisource/*.json，放在 sources/classic_list/ctext/。

  python3 tools/fetch_classics_ctext.py [slug ...]

ctext 对高频抓取会出验证码，fetch_ctext_books.get 每页间隔 7 秒；只取用户指明的单页，不做检索。
繁体转简体用 opencc t2s，不校改文字（ctext 的这些页多是字符识别的初稿，疑误处在注里说明）。
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fetch_ctext_books as f

OUT = ROOT / "sources/classic_list/ctext"
# slug: (篇名, ctext 章节页 chapter 编号)
PAGES = {"jiezhulou": ("借竹楼记", 388368), "yanglanshuo": ("养兰说", 392303), "yuyuanshipu": ("与袁石浦", 127846), "gaojieshuo": ("高洁说", 54286)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, (title, chapter) in PAGES.items():
        if len(sys.argv) > 1 and slug not in sys.argv[1:]:
            continue
        url = f"https://ctext.org/wiki.pl?if=gb&chapter={chapter}&remap=gb"
        h = f.get(url)
        s = BeautifulSoup(h, "html.parser")
        ptitle = re.sub(r"\s*-\s*中國哲學書電子化計劃.*$", "", s.title.get_text(" ", strip=True))
        blocks = [{"type": "p", "text": f.T2S.convert(t.strip())} for k, t in f.rows(h) if k == "P" and t.strip()]
        raw = "\n".join(b["text"] for b in blocks)
        data = {"title": f"{ptitle}（ctext）", "query": title, "url": url, "resolved_url": url, "revision": f"chapter={chapter}",
                "fetched_at": datetime.now(timezone.utc).isoformat(), "blocks": blocks,
                "text_sha256": hashlib.sha256(raw.encode("utf8")).hexdigest()}
        (OUT / f"{slug}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf8")
        print(slug, ptitle, chapter, len(blocks), len(raw))


if __name__ == "__main__":
    main()
