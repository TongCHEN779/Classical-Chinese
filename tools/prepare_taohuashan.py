"""Typeset Taohuashan music and recited verse separately from dialogue."""
import re
from prepare_sanyan import ROOT, layout, load, meter

SLUG = "taohuashan"
TUNE = re.compile(r"【[^】]+】|〔[^〕]+〕")
RECITAL = re.compile(r"^((?:\([^()]+\))*)((?:[^，；。！？()“”]{5,7}[，；。！？]){2,4})")
ZHEGU_CI = "院静厨寒睡起迟，秣陵人老看花时；城连晓雨枯陵树，江带春潮坏殿基。伤往事，写新词，客愁乡梦乱如丝。不知烟水西村舍，燕子今年宿傍谁？"


def chapter_rows(page):
    drama = page["slug"].startswith("p")
    for b in page["blocks"]:
        lines = b["lines"]
        text = "".join(lines)
        if not drama:
            yield "原", "/".join(lines)
            continue
        if b["verse"]:
            yield "诗", layout(lines)
            continue
        if m := TUNE.search(text):
            if m.start():
                yield "原", text[:m.start()]
            yield "诗", layout([text[m.start():]])
            continue
        if text.startswith("(鹧鸪天)" + ZHEGU_CI):
            yield "诗", layout(["(鹧鸪天)" + ZHEGU_CI])
            if rest := text[len("(鹧鸪天)" + ZHEGU_CI):]:
                yield "原", rest
            continue
        if m := RECITAL.match(text):
            lengths = meter(m[2])
            if len(lengths) in (2, 4) and len(set(lengths)) == 1 and m[2].endswith(("。", "！", "？")):
                if m[1]:
                    yield "原", m[1]
                yield "诗", layout([m[2]])
                if rest := text[m.end():]:
                    yield "原", rest
                continue
        yield "原", "/".join(lines)


def main():
    for p in load(SLUG):
        target = ROOT / "src" / SLUG / p["slug"] / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f"{kind}：{text}\n" for kind, text in chapter_rows(p))
        target.write_text(f"# {p['title']}\n" + body, encoding="utf8")


if __name__ == "__main__":
    main()
