"""Verify the Zhouli pages preserve the cached original and align each hover."""
from hashlib import sha256
import json

from bs4 import BeautifulSoup
from prepare_zhouli import BASE, ROOT, TITLES, load
from build import BOOK_INTRO, WIKI_INTRO, split_notes, split_sents


def html(path):
    return BeautifulSoup((ROOT / path).read_text(encoding="utf8"), "html.parser")


def main():
    catalog = json.loads((BASE / "catalog.json").read_text(encoding="utf8"))
    assert tuple(p["title"] for p in catalog) == TITLES
    directory = html("zhouli/index.html")
    assert [a["href"] for a in directory.select("main li.ok a")] == [p["slug"] + ".html" for p in catalog]
    assert directory.select_one("header p.intro").get_text() == WIKI_INTRO["zhouli"]["text"]
    home = html("index.html")
    assert any(BOOK_INTRO["zhouli"] in a.get_text() for a in home.select('a[href="zhouli/index.html"]'))
    assert WIKI_INTRO["zhouli"]["text"] not in home.get_text()
    for p in catalog:
        slug = p["slug"]
        source, rows = load(slug)
        digest = sha256("\n".join(b["text"] for b in source["blocks"]).encode()).hexdigest()
        assert digest == source["text_sha256"] and p["revision"] == source["revision"], slug
        originals = [(i, text) for i, tag, text in rows if tag in ("p", "li")]
        normalized = sha256("\n".join(text for _, text in originals).encode()).hexdigest()
        assert normalized == p["sha256"], slug
        doc = html(f"zhouli/{slug}.html")
        paragraphs = doc.select("section.entry p.v")
        assert len(paragraphs) == len(originals) == p["paragraphs"], slug
        assert [x.get_text() for x in paragraphs] == [text for _, text in originals], slug
        assert doc.select_one(".intro-box p").get_text().strip(), slug
        path = BASE / f"{slug}-annotations.json"
        annotations = json.loads(path.read_text(encoding="utf8"))["段落"] if path.exists() else {}
        count = translated = 0
        for (i, original), element in zip(originals, paragraphs):
            spans = element.select("span.s[data-t]")
            expected = annotations.get(str(i), {}).get("译", [])
            assert [s["data-t"] for s in spans] == expected, (slug, i)
            assert [s.get_text() for s in spans] == (split_sents(original) if expected else []), (slug, i)
            count += len(spans)
            translated += bool(spans)
        assert (count, translated) == (p["sentences"], p["translated"]), slug
        assert translated == len(originals), (slug, "正文仍有未配白话的段落")
        notes = [n for i, _ in originals for note in annotations.get(str(i), {}).get("注", [])
                 for n in split_notes(note)]
        assert sorted(li.get_text() for li in doc.select(".notes.plain li")) == sorted(notes)   # 注释按正文上标顺序排列，故不比顺序, slug
    print(f"《周礼》六篇底本与简介校验通过；已核对 {sum(p['sentences'] for p in catalog)} 句悬浮译文。")


if __name__ == "__main__":
    main()
