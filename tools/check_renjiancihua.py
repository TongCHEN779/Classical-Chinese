"""核验《人间词话》：正文与维基文库快照逐段一致，注释逐条照录原页面，不含自撰白话/题解。"""
import sys
from bs4 import BeautifulSoup

from prepare_renjiancihua import ROOT, read

sys.path.insert(0, str(ROOT))
from build import BOOK_INTRO


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    data = read()
    pages = data["pages"]
    assert [p["slug"] for p in pages] == ["shang", "xia", "buyi"]
    index = html("renjiancihua/index.html")
    assert [a["href"] for a in index.select("main li.ok a")] == [f"{p['slug']}.html" for p in pages]
    assert html("index.html").select_one('a[href="renjiancihua/index.html"] p').get_text() == BOOK_INTRO["renjiancihua"]
    secs = paras = notes = 0
    for p in pages:
        doc = html(f"renjiancihua/{p['slug']}.html")
        entries = doc.select("section.entry")
        assert len(entries) == len(p["sections"]), p["slug"]
        assert not doc.select(".s[data-t]") and not doc.select(".intro-box"), "不应有白话或题解"
        src_paras = [q for s in p["sections"] for q in s["paragraphs"]]
        assert [x.get_text().strip() for x in doc.select("section.entry p.v")] == [q["text"] for q in src_paras], p["slug"]
        assert [li.get_text() for li in doc.select(".notes.plain li")] == [n for q in src_paras for n in q["notes"]], p["slug"]
        secs += len(entries)
        paras += len(src_paras)
        notes += len(doc.select(".notes.plain li"))
    print(f"《人间词话》核验通过：{secs} 则、{paras} 段、{notes} 条原站注释。")


if __name__ == "__main__":
    main()
