"""Build the 56 chapters from the pinned Wikisource reading text."""
import json
import re
from prepare_jinpingmei import ROOT

# In this witness, definition lists also hold letters and official documents.
VERSE_BLOCKS = {("001", 0), ("007", 13), ("009", 14), ("015", 1), ("056", 24)}
COUPLETS = {
    ("022", 17): "“读书好，耕田好，学好便好﹔创业难，守成难，知难不难”",
    ("028", 1): "“清风明月常如此，才子佳人信有之。”",
}
ENDING_LABEL = re.compile(r"〈\(维基编入者著:\s*(五十[五六]回)版本\)〉")

def rows(chapter):
    slug = chapter["slug"]
    for i, block in enumerate(chapter["blocks"]):
        lines = block["lines"]
        key = slug, i
        if key in VERSE_BLOCKS:
            yield True, "/".join(lines)
            continue
        if slug == "055" and (match := ENDING_LABEL.fullmatch(lines[0])):
            yield False, f"【{match[1]}本结尾】"
            lines = lines[1:]
        if key in COUPLETS:
            couplet = COUPLETS[key]
            before, found, after = "/".join(lines).partition(couplet)
            assert found and before and after, key
            yield False, before
            yield True, re.sub(r"(?<=[﹔，])(?=[^﹔，]*”$)", "/", couplet)
            yield False, after
        elif key in {("055", 11), ("056", 25)}:
            before, sep, lyric = "".join(lines).partition("词曰：")
            assert sep and lyric, key
            yield False, before + sep
            yield True, "/".join(re.split(r"(?<=[。！？])(?=.)", lyric))
        else:
            yield False, "/".join(lines)

def main():
    chapters = json.loads((ROOT / "sources/rulinwaishi/chapters.json").read_text())
    assert [p["slug"] for p in chapters] == [f"{n:03}" for n in range(1, 57)]
    for p in chapters:
        assert p["revision"] and p["blocks"]
        dest = ROOT / "src/rulinwaishi" / p["slug"] / "01.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f'{"诗" if marked else "原"}：{text}\n' for marked, text in rows(p))
        dest.write_text(f'# {p["title"]}\n{body}', encoding="utf8")

if __name__ == "__main__":
    main()
