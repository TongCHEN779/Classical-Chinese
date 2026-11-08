"""Prepare five late-Qing novels as original prose and centered verse."""
from prepare_sanyan import ROOT, load, rows

BOOKS = {
    "lengyanguan": ("冷眼观", 30),
    "jieyuhui": ("劫餘灰", 16),
    "houguanchang": ("后官场现形记", 8),
    "zuijinguanchang": ("最近官场秘密史", 32),
    "jinshehui": ("近世社会龌龊史", 20),
}
# Longer couplet lines or lines without punctuation need explicit layout.
FORCED = {
    ("lengyanguan", "p002"): (23, 24),
    ("lengyanguan", "p025"): (2, 3),
}

PROSE = {("houguanchang", "p001"): (6,), ("jinshehui", "p003"): (8, 16),
         ("jinshehui", "p007"): (15,)}

def chapter_rows(book, chapter):
    selected = FORCED.get((book, chapter["slug"]), ())
    blocks = []
    for i, block in enumerate(chapter["blocks"]):
        if i in selected:
            block = {**block, "verse": True}
        blocks.append(block)
    prose = {"".join(blocks[i]["lines"]) for i in PROSE.get((book, chapter["slug"]), ())}
    if (book, chapter["slug"]) == ("jinshehui", "p003"):
        prose.add("“这件事倘使徒事游移，是一定弄不好的，我劝你早定主意的好。”")
    for kind, text in rows(blocks):
        if kind == "诗" and text.replace("/", "") in prose:
            kind = "原"
        yield kind, text


def main():
    for book, (_, count) in BOOKS.items():
        chapters = load(book)
        expected = (["xu"] if book == "jinshehui" else []) + [f"p{n:03}" for n in range(1, count + 1)]
        assert [p["slug"] for p in chapters] == expected
        for p in chapters:
            path = ROOT / "src" / book / p["slug"] / "01.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            body = "".join(f"{kind}：{text}\n" for kind, text in chapter_rows(book, p))
            path.write_text(f"# {p['title']}\n" + body, encoding="utf8")


if __name__ == "__main__":
    main()
