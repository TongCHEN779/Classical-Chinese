"""核验《长生殿》：五十出正文与维基文库快照逐块一致，每出有题解，注释齐全可定位。"""
import sys
from bs4 import BeautifulSoup

from prepare_changshengdian import BASE, ROOT, read

sys.path.insert(0, str(ROOT))


def html(path):
    return BeautifulSoup((ROOT / path if (ROOT / path).exists() else ROOT / "books" / path).read_text(encoding="utf8"), "html.parser")


def main():
    chapters = read(BASE / "chapters.json")
    assert [c["slug"] for c in chapters] == [f"c{i:02}" for i in range(1, 51)]
    index = html("changshengdian/index.html")
    assert [a["href"] for a in index.select("main li.ok a")] == [f"{c['slug']}.html" for c in chapters]
    notes = 0
    for c in chapters:
        doc = html(f"changshengdian/{c['slug']}.html")
        assert [p.get_text().strip() for p in doc.select("section.entry p.v")] == [b["text"].replace("/", "") for b in c["blocks"]], c["slug"]
        assert doc.select_one(".intro-box p"), f"{c['slug']} 缺题解"
        assert not doc.select(".s[data-t]"), "本书不配白话"
        n = len(doc.select(".notes.plain li"))
        assert n >= 3, f"{c['slug']} 注释过少"
        notes += n
    print(f"《长生殿》核验通过：{len(chapters)} 出，{notes} 条注释。")


if __name__ == "__main__":
    main()
