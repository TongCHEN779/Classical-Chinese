"""Typeset Taohuashan using the witness paragraph and line boundaries."""
from prepare_sanyan import ROOT, load

SLUG = "taohuashan"


def chapter_rows(page):
    # The witness already records paragraphs and explicit line breaks. A tune
    # label or a metrical opening does not create another paragraph.
    drama = page["slug"].startswith("p")
    for block in page["blocks"]:
        kind = "诗" if drama and block["verse"] else "原"
        yield kind, "/".join(block["lines"])


def main():
    for p in load(SLUG):
        target = ROOT / "src" / SLUG / p["slug"] / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f"{kind}：{text}\n" for kind, text in chapter_rows(p))
        target.write_text(f"# {p['title']}\n" + body, encoding="utf8")


if __name__ == "__main__":
    main()
