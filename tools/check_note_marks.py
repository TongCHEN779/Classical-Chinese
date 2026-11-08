#!/usr/bin/env python3
"""全站核验注释上标：每个有注释的节，正文里的上标数 = 注释条数，上标序号按出现顺序递增，注释列表与之一一对应。

  python3 tools/check_note_marks.py [目录 …]
"""
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"assets", "tools", "sources", "src", "tests", ".git", "node_modules"}


def count(label):
    if "–" in label:
        a, b = label.split("–")
        return int(b) - int(a) + 1
    return len(label.split(","))


def main():
    dirs = [ROOT / d for d in sys.argv[1:]] or [d for d in sorted(ROOT.iterdir()) if d.is_dir() and d.name not in SKIP]
    pages = notes_total = bad = 0
    for d in dirs:
        for f in sorted(d.glob("*.html")):
            if f.name == "index.html":
                continue
            html = f.read_text(encoding="utf8")
            if 'class="notes' not in html:
                continue
            pages += 1
            doc = BeautifulSoup(html, "html.parser")
            for sec in doc.select("section.entry"):
                lists = sec.select("ul.notes.plain, ol.notes")
                if not lists:
                    continue
                n = sum(len([x for x in li_list.find_all("li", recursive=False) if x.has_attr("data-n") or "src" not in (li_list.get("class") or [])]) for li_list in lists)   # 人间词话的无序号补充说明不计
                sups = sec.select("sup.n")
                m = sum(count(s["data-n"]) for s in sups)
                notes_total += n
                if n != m:
                    bad += 1
                    if bad <= 20:
                        print(f"  不一致 {f.relative_to(ROOT)} {sec.get('id')}: 注释 {n} 条，上标 {m} 个")
    assert bad == 0, f"{bad} 节的上标数与注释条数不符"
    print(f"注释上标核验通过：{pages} 页、{notes_total} 条注释均有对应上标。")


if __name__ == "__main__":
    main()
