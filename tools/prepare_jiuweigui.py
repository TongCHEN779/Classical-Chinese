"""Generate the 192 reading chapters of Jiuweigui from its pinned text."""
import json
import re
from prepare_three_novels import ROOT, metrical, rows

# Distinguish a quoted verse from ordinary dialogue introduced by 沉吟道.
RECITED = re.compile(r"(?:高吟道|低吟道|微吟道|诗曰|词曰|诗云|联云|联曰)[：:]([“「])([^”」]{8,120})([”」])")

def reading_rows(blocks):
    for marked, text in rows(blocks):
        if marked:
            yield marked, text
            continue
        start = 0
        for match in RECITED.finditer(text):
            if not metrical(match[2]):
                continue
            yield False, text[start:match.start(1)]
            quote = match[1] + match[2] + match[3]
            yield True, re.sub(r"(?<=[，。！？；])(?=[^，。！？；”」]+)", "/", quote)
            start = match.end()
        if start < len(text):
            yield False, text[start:]

def main():
    chapters = json.loads((ROOT / "sources/jiuweigui/chapters.json").read_text())
    assert [p["slug"] for p in chapters] == [f"{n:03}" for n in range(1, 193)]
    for p in chapters:
        assert p["revision"] and p["blocks"]
        dest = ROOT / "src/jiuweigui" / p["slug"] / "01.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f'{"诗" if marked else "原"}：{text}\n' for marked, text in reading_rows(p["blocks"]))
        dest.write_text(f'# {p["title"]}\n{body}', encoding="utf8")

if __name__ == "__main__":
    main()
