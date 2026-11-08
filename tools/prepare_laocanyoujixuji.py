"""Prepare the original sequel, preserving separately typeset poems and couplets."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "sources/laocanyoujixuji"
VERSE_RUNS = {"p05": {14: 2}, "p09": {11: 4}}
INLINE = {
    ("p05", 12): "‘一切有为法，如梦幻泡影，如露亦如电，应作如是观。’",
    ("p06", 20): "“荒村雨露眠宜早，野店风霜起要迟”",
}


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf8"))


def originals(slug):
    return [b["text"] for b in read(slug + ".json")["blocks"] if b["type"] == "p"]


def paragraphs(slug):
    inserts = read("verse-blocks.json").get(slug, {})
    runs = VERSE_RUNS.get(slug, {})
    text = originals(slug)
    i = 0
    while i <= len(text):
        if lines := inserts.get(str(i)):
            yield "诗", "/".join(lines)
        if i == len(text):
            break
        if count := runs.get(i):
            yield "诗", "/".join(text[i:i+count])
            i += count
            continue
        para = text[i]
        if quote := INLINE.get((slug, i)):
            before, match, after = para.partition(quote)
            assert match, (slug, i)
            if before:
                yield "原", before
            yield "诗", re.sub(r"(?<=，)", "/", quote)
            if after:
                yield "原", after
        else:
            yield "原", para
        i += 1


def main():
    for entry in read("catalog.json"):
        slug = entry["slug"]
        path = ROOT / "src/laocanyoujixuji" / slug / "01.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f"{kind}：{text}\n" for kind, text in paragraphs(slug))
        path.write_text(f"# {entry['title']}\n" + body, encoding="utf8")


if __name__ == "__main__":
    main()
