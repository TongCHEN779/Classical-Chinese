"""Generate the five late Qing novel reading editions from saved witnesses."""
import json
from prepare_three_novels import ROOT
from prepare_jiuweigui import reading_rows

COUNTS = {"niehaihua": 35, "shangjie": 16, "nianzaifanhuameng": 40,
          "facaimijue": 10, "fupuxiantan": 30}

def main():
    for book, count in COUNTS.items():
        chapters = json.loads((ROOT / "sources" / book / "chapters.json").read_text())
        prefix = ["xu"] if book == "nianzaifanhuameng" else []
        assert [p["slug"] for p in chapters] == prefix + [f"{n:03}" for n in range(1, count + 1)]
        for p in chapters:
            assert p["revision"] and p["blocks"]
            dest = ROOT / "src" / book / p["slug"] / "01.txt"
            dest.parent.mkdir(parents=True, exist_ok=True)
            blocks = p["blocks"]
            if (book, p["slug"]) == ("shangjie", "016"):
                # The source's poem wrapper here contains a shareholder roster.
                blocks = [{**b, "poem": False} if b["poem"] and b["lines"][0] == "胡君　须德" else b
                          for b in blocks]
            body = "".join(f'{"诗" if marked else "原"}：{text}\n' for marked, text in reading_rows(blocks))
            dest.write_text(f'# {p["title"]}\n{body}', encoding="utf8")

if __name__ == "__main__":
    main()
