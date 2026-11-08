"""由 sources/renjiancihua/chapters.json（维基文库《人间词话》汇本：正文及原页面自带的①②…注释）生成 src/renjiancihua/*/01.txt。
不设白话、题解，也不增补任何注释：每则只有原文，注释逐条照录维基文库原页面。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "sources/renjiancihua"


def read():
    return json.loads((BASE / "chapters.json").read_text(encoding="utf8"))


def main():
    for page in read()["pages"]:
        lines = []
        for sec in page["sections"]:
            lines.append(f"# {sec['title']}")
            for para in sec["paragraphs"]:
                lines.append(f"原：{para['text']}")
                lines.extend(f"注原：{n}" for n in para["notes"])  # “注原：”=照录原站注释，build 不再拆分
        target = ROOT / "src/renjiancihua" / page["slug"] / "01.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf8")
        print(page["slug"], len(page["sections"]), "则")


if __name__ == "__main__":
    sys.exit(main())
