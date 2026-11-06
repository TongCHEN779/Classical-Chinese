"""Generate the three white-language novel reading editions from saved witnesses."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {"guanchang": 60, "chuke": 40, "erke": 40}
CUE = re.compile(r"(?:诗|词|联|曲|歌|赞|唱|吟)(?:曰|道|云|为证)?[：:]$")
INLINE = re.compile(r"(?:对联|门联|楹联)[^。！？「」“”]{0,28}(?:[：:]|写著|写着|题著|题着)([「“])([^」”]{7,65})([」”])")
CLAUSE = re.compile(r"[，、。！？；﹔：]")
BREAK = re.compile(r"(?<=[。！？；﹔])(?=.)")

def metrical(text):
    parts = [x.strip("「」『』“”　 ") for x in CLAUSE.split(text) if x.strip("「」『』“”　 ")]
    return len(parts) >= 2 and len(parts) % 2 == 0 and len(set(map(len, parts))) == 1 and 4 <= len(parts[0]) <= 9

def rows(blocks):
    previous = ""
    for b in blocks:
        lines = b["lines"]
        text = "".join(lines)
        clauses = [x for x in CLAUSE.split(text) if x]
        short_lines = bool(clauses) and len(clauses) >= 2 and sum(map(len, clauses)) <= 10 * len(clauses)
        stanza = (b["poem"] or metrical(text) or
                  ((b["deep_indent"] or b["layout"] in {"dl", "pre", "center"}) and short_lines
                   and not re.search(r"^(话说|却说|且说|再说)", text)) or
                  (CUE.search(previous) and len(text) <= 330 and not re.search(r"^(话说|却说|且说|再说)", text)))
        if stanza and not b["poem"] and "下回分解" in text:
            stanza = False
        if stanza:
            yield True, "/".join(lines if len(lines) > 1 else BREAK.split(text))
        else:
            start = 0
            joined = "/".join(lines)
            for m in INLINE.finditer(joined):
                yield False, joined[start:m.start(1)]
                yield True, m[1] + re.sub(r"(?<=[，；﹔])(?=[^，；﹔]+$)", "/", m[2]) + m[3]
                start = m.end()
            if start < len(joined):
                yield False, joined[start:]
        previous = text

def source_lines(book, blocks, slug=None):
    if book == "chuke" and blocks and re.match(r"^第[一二三四五六七八九十百]+卷\s",
                                                blocks[0]["lines"][0]):
        blocks = blocks[1:]
    if (book, slug) == ("erke", "040"):
        for block in blocks:
            yield "原：" + "/".join(block["lines"])
        return
    if (book, slug) == ("erke", "006"):
        blocks = [{**b, "lines": ["".join(b["lines"])], "poem": False, "deep_indent": False, "layout": "p"}
                  if b["lines"][0].startswith("这四句乃是白乐天") else b for b in blocks]

    for marked, text in rows(blocks):
        if book == "guanchang":
            note = re.fullmatch(r"〈（(.+?)）〉(.*)", text)
            if note:
                yield "注：" + note[1] + note[2]
                continue
            # Some notes use ordinary outer parentheses and bracket inner glosses.
            note = re.fullmatch(r"（([^：]+：.+)）", text)
            if note and "〈（" in note[1]:
                yield "注：" + note[1].replace("〈（", "（").replace("）〉", "）")
                continue
        yield f'{"诗" if marked else "原"}：{text}'


def main():
    for book, count in COUNTS.items():
        chapters = json.loads((ROOT / "sources" / book / "chapters.json").read_text())
        assert [p["slug"] for p in chapters] == (["xu"] if book == "erke" else []) + [f"{n:03}" for n in range(1, count + 1)]
        for p in chapters:
            assert p["revision"] and p["blocks"]
            dest = ROOT / "src" / book / p["slug"] / "01.txt"
            dest.parent.mkdir(parents=True, exist_ok=True)
            body = "\n".join(source_lines(book, p["blocks"], p["slug"])) + "\n"
            dest.write_text(f'# {p["title"]}\n{body}', encoding="utf8")

if __name__ == "__main__":
    main()
