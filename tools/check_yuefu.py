"""核验《乐府诗集》：已完成的卷，正文与维基文库快照逐段一致，逐句白话齐全，每节有题解。"""
import sys
from bs4 import BeautifulSoup

from prepare_yuefu import BASE, ROOT, read

sys.path.insert(0, str(ROOT))
from build import split_sents


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    chapters = read(BASE / "chapters.json")
    assert [c["slug"] for c in chapters] == [f"j{i:03}" for i in range(1, 101)]
    done = read(BASE / "progress.json")["complete"] if (BASE / "progress.json").exists() else []
    if not done:
        print("《乐府诗集》尚无完成的卷。")
        return
    index = html("yuefu/index.html")
    assert [a["href"] for a in index.select("main li.ok a")] == [f"{s}.html" for s in done]
    total = notes = 0
    for c in chapters:
        if c["slug"] not in done:
            continue
        slug = c["slug"]
        paras = [p for s in c["sections"] for p in s["paragraphs"]]
        doc = html(f"yuefu/{slug}.html")
        assert [p.get_text().strip() for p in doc.select("section.entry p.v")] == [p.strip() for p in paras], slug
        spans = doc.select("section.entry .s[data-t]")
        assert [s.get_text() for s in spans] == [x for p in paras for x in split_sents(p)], slug
        assert all(s["data-t"].strip() for s in spans), slug
        assert len(doc.select("section.entry")) == len(c["sections"]), slug
        assert all(e.select_one(".intro-box p") for e in doc.select("section.entry")), slug
        total += len(spans)
        notes += len(doc.select(".notes.plain li"))
    print(f"《乐府诗集》已完成 {len(done)}/100 卷核验通过：{total} 句白话，{notes} 条注释。")


if __name__ == "__main__":
    main()
