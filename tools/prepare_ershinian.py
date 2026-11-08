"""Typeset the 108 chapters of Ershi Nian as original prose and centered verse."""
from pathlib import Path
import re

from prepare_sanyan import ROOT, load, rows

SLUG = "ershinian"
# These quotations are introduced by narration too far from the actual verse
# for the general verse detector to associate them.
QUOTES = {
    "p016": ("‘两个是傅粉何郎，两个是画眉张敞。’",),
    "p017": ("‘三字官箴凭隔膜，八行京信便通神。’",),
    "p022": ("‘灌向瓮中何必井，来从湖上不须舟’",),
    "p027": ("‘心中乌黑嘴明白，腰上鹅黄顶暗蓝。’",),
    "p033": ("‘骚人韵士，絮果兰因’",),
}


def chapter_rows(chapter):
    quotes = QUOTES.get(chapter["slug"], ())
    for kind, text in rows(chapter["blocks"]):
        if kind == "原":
            for quote in quotes:
                before, sep, after = text.partition(quote)
                if not sep:
                    continue
                if before:
                    yield "原", before
                yield "诗", re.sub("，", "，/", quote, count=1)
                text = after
        if kind == "原":
            m = re.match(r"^(正是[：:])([^，。！？；]{4,9}，)([^，。！？；]{4,9}[。！？])(.*)$", text)
            if m and len(m[2]) == len(m[3]):
                yield "原", m[1]
                yield "诗", m[2] + "/" + m[3]
                text = m[4]
        if text:
            yield kind, text


def main():
    chapters = load(SLUG)
    assert [p["slug"] for p in chapters] == [f"p{i:03}" for i in range(1, 109)]
    for p in chapters:
        target = ROOT / "src" / SLUG / p["slug"] / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(f"{kind}：{text}\n" for kind, text in chapter_rows(p))
        target.write_text(f"# {p['title']}\n" + content, encoding="utf8")


if __name__ == "__main__":
    main()
