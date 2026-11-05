"""Render the pinned Chongzhen witness as prose and explicitly marked verse."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "sources/jinpingmei"
BREAK = re.compile(r"(?<=[。！？；])")
CLAUSE = re.compile(r"[，。！？；、：]")
CUE = re.compile(r"(?:诗|词|曲|联|赞|歌|赋|有诗|有词)(?:曰|道|云|为证)?[：:]$")

def verse(block, previous):
    text = "".join(block["lines"])
    if block["poem"]:
        return True
    if "下回分解" in text or "下回便见" in text:
        return False
    clauses = [x for x in CLAUSE.split(text) if x]
    if not clauses:
        return False
    if CUE.search(previous) and len(text) <= 450:
        return True
    if block["indent"]:
        return len(text) <= 450
    if re.search(r"[“”「」『』]", text):
        return False
    if len(clauses) in (2, 4, 8) and len(set(map(len, clauses))) == 1:
        return 4 <= len(clauses[0]) <= 9 and bool(re.search(r"[，；]", text))
    return False

def rows(blocks):
    previous = ""
    for block in blocks:
        lines = block["lines"]
        text = "".join(lines)
        is_verse = verse(block, previous)
        if is_verse and len(lines) == 1:
            lines = [line for line in BREAK.split(text) if line]
        yield is_verse, "/".join(lines)
        previous = text

def main():
    chapters = json.loads((BASE / "chapters.json").read_text())
    assert [p["slug"] for p in chapters] == ["xu", *(f"{n:03}" for n in range(1, 101))]
    for p in chapters:
        assert p["revision"] and p["blocks"]
        dest = ROOT / "src/jinpingmei" / p["slug"] / "01.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f'{"诗" if marked else "原"}：{text}\n' for marked, text in rows(p["blocks"]))
        dest.write_text(f'# {p["title"]}\n{body}', encoding="utf8")

if __name__ == "__main__":
    main()
