"""Build the Sanyan reading texts from cached paragraphs and layout cues."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BOOKS = {"yushimingyan": "喻世明言", "jingshitongyan": "警世通言", "xingshihengyan": "醒世恒言"}
CUE = re.compile(r"(?:对联|对子|楹联|联语|一联|一诗|一词|一偈|诗曰|词曰|偈曰|诗云|偈云|联云|联曰)[^。！？“”「」『』]{0,16}[：:，]?([“「『])([^“”「」『』]{8,150})([”」』])")
CLAUSE = re.compile(r"[，。！？；、：,.!?;:]")
CONTINUATION = re.compile(r"^(?:话说|且说|却说|看官|原来|只见|当下|未知|欲知|不知)")


def layout(lines):
    if len(lines) > 1:
        return "/".join(lines)
    text = lines[0]
    rows = [s for s in re.split(r"(?<=[。！？；])(?=[^”」』])", text) if s]
    if len(rows) == 1 and text.count("，") == 1:
        rows = re.split(r"(?<=，)", text)
    return "/".join(rows)


def meter(text):
    return [len(s) for s in CLAUSE.split(text) if s]


def verse(block, previous):
    if block["verse"]:
        return True
    text = "".join(block["lines"])
    if not text or len(text) > 300 or CONTINUATION.match(text) or "下回分解" in text:
        return False
    lengths = meter(text)
    if len(lengths) < 2 or re.search(r'[“”「」『』]', text):
        return False
    tight = max(lengths) <= 10
    regular = tight and len(set(lengths)) == 1 and lengths[0] in (4, 5, 6, 7, 8)
    cue = bool(re.search(r"(?:诗|词|联|偈|曲|赞|有分教|正是|怎见得)[^。！？]{0,13}[：:]$", previous))
    return regular or (tight and (block["indent"] >= 3 or cue or len(block["lines"]) > 1))


def unwrap(blocks):
    """Separate verse lines from hard-wrapped, plain-text witness blocks."""
    for block in blocks:
        lines = block["lines"]
        if block["verse"] or len(lines) < 5 or sum(map(len, lines)) < 190:
            yield block
            continue
        prose = ""
        for line in lines:
            lengths = meter(line)
            if len(lengths) in (2, 4, 8) and len(set(lengths)) == 1 and 4 <= lengths[0] <= 8:
                if prose:
                    yield {"lines": [prose], "verse": False, "indent": 0}
                    prose = ""
                yield {"lines": [line], "verse": True, "indent": 0}
            else:
                prose += line
                if len(prose) >= 350 and prose.endswith(("。", "？”", "！”", "。”")):
                    yield {"lines": [prose], "verse": False, "indent": 0}
                    prose = ""
        if prose:
            yield {"lines": [prose], "verse": False, "indent": 0}


def rows(blocks):
    previous = ""
    for block in unwrap(blocks):
        lines = block["lines"]
        text = "".join(lines)
        if verse(block, previous):
            yield "诗", layout(lines)
        else:
            pos = 0
            matches = []
            for m in CUE.finditer(text):
                quoted = m[1] + m[2] + m[3]
                sizes = meter(m[2])
                if len(sizes) < 2 or max(sizes) > 11:
                    continue
                matches.append((m.start(1), m.end(), quoted))
            for m in re.finditer(r"(?:诗曰|诗云|词曰|联曰|偈曰|诗赞[^：。]{0,15}|正是|有分教|有诗为证|分明是)[：:]", text):
                tail = text[m.end():]
                pairs = re.match(r"(?:[^，；。？！“”「」]{4,8}[，；。？！]){2,8}", tail)
                if not pairs:
                    continue
                sizes = meter(pairs[0])
                if len(sizes) in (2, 4, 6, 8) and len(set(sizes)) == 1:
                    matches.append((m.end(), m.end() + len(pairs[0]), pairs[0]))
            for start, end, quoted in sorted(matches):
                if start < pos:
                    continue
                if pos < start:
                    yield "原", text[pos:start]
                yield "诗", layout([quoted])
                pos = end
            if pos < len(text):
                yield "原", text[pos:]
        previous = text


def load(slug):
    return json.loads((ROOT / "sources" / slug / "chapters.json").read_text(encoding="utf8"))


def main():
    for book in BOOKS:
        chapters = load(book)
        assert [p["slug"] for p in chapters] == ["xu", *(f"p{n:02}" for n in range(1, 41))]
        for page in chapters:
            path = ROOT / "src" / book / page["slug"] / "01.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            content = "".join(f"{kind}：{t}\n" for kind, t in rows(page["blocks"]))
            path.write_text(f"# {page['title']}\n" + content, encoding="utf8")


if __name__ == "__main__":
    main()
