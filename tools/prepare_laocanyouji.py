"""Format the original text of Lao Can You Ji with explicit verse blocks."""
from collections import defaultdict
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "sources/laocanyouji"
INLINE = {
    ("xu", 1): ("“巴东三峡巫峡长，猿啼三声断人肠。”",),
    ("xu", 3): ("“别恨离愁，满肺腑，难淘泻，除纸笔，代喉舌，我千种相思向谁说？”",
                "“满纸荒唐言，一把辛酸泪，都云作者痴，谁解其中意？”"),
    ("p02", 3): ("“历下此亭古，济南名士多”",),
    ("p02", 5): ("“四面荷花三面柳，一城山色半城湖”", "“一盏寒泉荐秋菊，三更画舫穿藕花”"),
    ("p12", 8): ("“明月照积雪，北风劲且哀”",),
}


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf8"))


def originals(slug):
    return [b["text"] for b in read(slug + ".json")["blocks"] if b["type"] == "p"]


def paragraphs(slug):
    insertion = defaultdict(list)
    for block in read("verse-blocks.json").get(slug, []):
        insertion[block["before"]].append(block["lines"])
    for i, prose in enumerate([*originals(slug), ""]):
        for lines in insertion[i]:
            # The screen in chapter nine contains six quatrains.
            if slug == "p09":
                yield from (("诗", "/".join(lines[k:k+2])) for k in range(0, len(lines), 2))
            else:
                yield "诗", "/".join(lines)
        if not prose:
            continue
        if slug == "p10" and 9 <= i <= 13:
            yield "诗", re.sub(r"(?<=[；。])(?=.)", "/", prose)
            continue
        for quote in INLINE.get((slug, i), ()):
            before, sep, after = prose.partition(quote)
            assert sep, (slug, i, quote)
            if before:
                yield "原", before
            delimiter = "，" if quote.count("，") == 1 else ("泪，" if "辛酸泪，" in quote else "难淘泻，")
            left, sep, right = quote.partition(delimiter)
            assert sep
            yield "诗", left + sep + "/" + right
            prose = after
        if prose:
            yield "原", prose


def main():
    for entry in read("catalog.json"):
        slug = entry["slug"]
        path = ROOT / "src/laocanyouji" / slug / "01.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = "".join(f"{kind}：{text}\n" for kind, text in paragraphs(slug))
        path.write_text(f"# {entry['title']}\n" + lines, encoding="utf8")


if __name__ == "__main__":
    main()
