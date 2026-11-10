"""核验《方言》：原文与维基文库快照一致（卷一至四仅去掉郭璞〈夹注〉并原样入注释）、逐句白话齐全。"""
import sys
from bs4 import BeautifulSoup

from prepare_fangyan import BASE, JUAN, ROOT, read, split_guo

sys.path.insert(0, str(ROOT))
from build import split_sents


def html(path):
    return BeautifulSoup((ROOT / path if (ROOT / path).exists() else ROOT / "books" / path).read_text(encoding="utf8"), "html.parser")


def main():
    chapters = read(BASE / "chapters.json")
    assert [c["slug"] for c in chapters] == ["xu", "kexu", *(f"p{i:02}" for i in range(1, 14)), "ba"]
    index = html("fangyan/index.html")
    assert [a["href"] for a in index.select("main li.ok a")] == [f"{c['slug']}.html" for c in chapters]
    total = 0
    for c in chapters:
        slug = c["slug"]
        guo = bool(JUAN.match(slug))
        pairs = [split_guo(p) if guo else (p, []) for p in c["paragraphs"]]
        doc = html(f"fangyan/{slug}.html")
        rendered = doc.select("section.entry p.v")
        assert [p.get_text().strip() for p in rendered] == [o.strip() for o, _ in pairs], slug
        spans = doc.select("section.entry .s[data-t]")
        expect = [s for o, _ in pairs for s in split_sents(o)]
        assert [s.get_text() for s in spans] == expect, slug
        assert all(s["data-t"].strip() for s in spans), slug
        notes = [li.get_text() for li in doc.select(".notes.plain li")]
        n_guo = sum(len(n) for _, n in pairs)
        assert sum("郭璞注“" in x for x in notes) == n_guo, (slug, n_guo)
        total += len(spans)
    print(f"《方言》核验通过：{total} 句白话。")


if __name__ == "__main__":
    main()
